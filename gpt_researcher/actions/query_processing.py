import json_repair

from gpt_researcher.llm_provider.generic.base import ReasoningEfforts
from ..utils.llm import create_chat_completion
from ..prompts import PromptFamily
from typing import Any, List, Dict
from ..config import Config
import logging

logger = logging.getLogger(__name__)

async def detect_and_translate_query(query: str, cfg=None, cost_callback: callable = None) -> tuple[str, str]:
    """
    Detect if query is non-English and translate to English if needed.
    
    Args:
        query: The original query
        cfg: Configuration object
        cost_callback: Callback for cost calculation
    
    Returns:
        Tuple of (processed_query, original_language)
    """
    import re
    
    # Quick check if query contains non-ASCII characters (likely non-English)
    if not re.match(r'^[\x00-\x7F]+$', query):
        logger.info(f"Detected non-English query, translating to English for better search results")
        
        try:
            # Use LLM to detect language and translate
            detection_prompt = f"""Analyze this query and respond in JSON format:
            Query: {query}
            
            Respond with:
            {{
                "language": "detected language name",
                "is_english": false,
                "english_translation": "translated query to English",
                "search_optimized_query": "optimized English query for web search"
            }}
            
            For search_optimized_query, make it search-engine friendly by:
            - Removing filler words
            - Focusing on key terms
            - Adding relevant English keywords"""
            
            response = await create_chat_completion(
                model=cfg.fast_llm_model if cfg else "gpt-4o-mini",
                messages=[{"role": "user", "content": detection_prompt}],
                temperature=0.1,
                llm_provider=cfg.fast_llm_provider if cfg else "openai",
                llm_kwargs=cfg.llm_kwargs if cfg else {},
                cost_callback=cost_callback
            )
            
            result = json_repair.loads(response)
            
            if not result.get("is_english", True):
                translated_query = result.get("search_optimized_query", result.get("english_translation", query))
                logger.info(f"Translated query from {result.get('language', 'unknown')} to English: {translated_query}")
                return translated_query, result.get("language", "unknown")
                
        except Exception as e:
            logger.warning(f"Failed to translate query: {e}, using original")
            
    return query, "english"

async def get_search_results(query: str, retriever: Any, query_domains: List[str] = None, researcher=None) -> List[Dict[str, Any]]:
    """
    Get web search results for a given query.

    Args:
        query: The search query
        retriever: The retriever instance
        query_domains: Optional list of domains to search
        researcher: The researcher instance (needed for MCP retrievers)

    Returns:
        A list of search results
    """
    # Check if this is an MCP retriever and pass the researcher instance
    if "mcpretriever" in retriever.__name__.lower():
        search_retriever = retriever(
            query, 
            query_domains=query_domains,
            researcher=researcher  # Pass researcher instance for MCP retrievers
        )
    else:
        search_retriever = retriever(query, query_domains=query_domains)
    
    # Handle LinkedIn with fallback to Tavily
    if "linkedin" in retriever.__name__.lower():
        logger.info("Using LinkedIn Sales Navigator retriever")
        results = search_retriever.search()
        
        # Check if LinkedIn search failed (returns None or empty list for rate limit/auth issues)
        if results is None or (isinstance(results, list) and len(results) == 0):
            logger.warning("LinkedIn search failed or returned no results, falling back to Tavily")
            
            # Import Tavily and use it as fallback
            from gpt_researcher.retrievers import TavilySearch
            
            # Detect and translate non-English queries for better Tavily results
            cfg = getattr(researcher, 'cfg', None) if researcher else None
            cost_callback = getattr(researcher, 'add_costs', None) if researcher else None
            translated_query, original_language = await detect_and_translate_query(query, cfg, cost_callback)
            
            # Use translated query if it's different from original
            if translated_query != query:
                logger.info(f"Using translated query for Tavily search: {translated_query}")
                # Add context about LinkedIn and the search intent
                enhanced_query = f"{translated_query} LinkedIn Sales Navigator profiles startups investment"
            else:
                # Add context about LinkedIn in the query for better Tavily results
                enhanced_query = f"{query} LinkedIn profiles Sales Navigator"
            
            tavily_retriever = TavilySearch(enhanced_query, query_domains=query_domains)
            
            try:
                results = tavily_retriever.search()
                logger.info(f"Tavily fallback search returned {len(results) if results else 0} results")
                
                # Add metadata to indicate these are fallback results
                if results:
                    for result in results:
                        if isinstance(result, dict):
                            result['source'] = 'Tavily (LinkedIn fallback)'
                            result['fallback_reason'] = 'LinkedIn returned no results'
                            if original_language != "english":
                                result['query_translated'] = True
                                result['original_language'] = original_language
            except Exception as e:
                logger.error(f"Tavily fallback also failed: {e}")
                results = []
        
        return results
    
    # For standard retrievers, also check if translation might help
    # This is especially useful for Tavily and other web search retrievers
    if "tavily" in retriever.__name__.lower() or "web" in retriever.__name__.lower():
        cfg = getattr(researcher, 'cfg', None) if researcher else None
        cost_callback = getattr(researcher, 'add_costs', None) if researcher else None
        translated_query, original_language = await detect_and_translate_query(query, cfg, cost_callback)
        
        if translated_query != query:
            logger.info(f"Using translated query for {retriever.__name__}: {translated_query}")
            search_retriever.query = translated_query
            
            # Store original query for reference
            if hasattr(search_retriever, 'original_query'):
                search_retriever.original_query = query
    
    # Standard retriever search
    return search_retriever.search()

async def generate_sub_queries(
    query: str,
    parent_query: str,
    report_type: str,
    context: List[Dict[str, Any]],
    cfg: Config,
    cost_callback: callable = None,
    prompt_family: type[PromptFamily] | PromptFamily = PromptFamily,
    **kwargs
) -> List[str]:
    """
    Generate sub-queries using the specified LLM model.

    Args:
        query: The original query
        parent_query: The parent query
        report_type: The type of report
        max_iterations: Maximum number of research iterations
        context: Search results context
        cfg: Configuration object
        cost_callback: Callback for cost calculation
        prompt_family: Family of prompts

    Returns:
        A list of sub-queries
    """
    gen_queries_prompt = prompt_family.generate_search_queries_prompt(
        query,
        parent_query,
        report_type,
        max_iterations=cfg.max_iterations or 3,
        context=context,
    )

    try:
        response = await create_chat_completion(
            model=cfg.strategic_llm_model,
            messages=[{"role": "user", "content": gen_queries_prompt}],
            llm_provider=cfg.strategic_llm_provider,
            max_tokens=None,
            llm_kwargs=cfg.llm_kwargs,
            reasoning_effort=ReasoningEfforts.Medium.value,
            cost_callback=cost_callback,
            **kwargs
        )
    except Exception as e:
        logger.warning(f"Error with strategic LLM: {e}. Retrying with max_tokens={cfg.strategic_token_limit}.")
        logger.warning(f"See https://github.com/assafelovic/gpt-researcher/issues/1022")
        try:
            response = await create_chat_completion(
                model=cfg.strategic_llm_model,
                messages=[{"role": "user", "content": gen_queries_prompt}],
                max_tokens=cfg.strategic_token_limit,
                llm_provider=cfg.strategic_llm_provider,
                llm_kwargs=cfg.llm_kwargs,
                cost_callback=cost_callback,
                **kwargs
            )
            logger.warning(f"Retrying with max_tokens={cfg.strategic_token_limit} successful.")
        except Exception as e:
            logger.warning(f"Retrying with max_tokens={cfg.strategic_token_limit} failed.")
            logger.warning(f"Error with strategic LLM: {e}. Falling back to smart LLM.")
            response = await create_chat_completion(
                model=cfg.smart_llm_model,
                messages=[{"role": "user", "content": gen_queries_prompt}],
                temperature=cfg.temperature,
                max_tokens=cfg.smart_token_limit,
                llm_provider=cfg.smart_llm_provider,
                llm_kwargs=cfg.llm_kwargs,
                cost_callback=cost_callback,
                **kwargs
            )

    return json_repair.loads(response)

async def plan_research_outline(
    query: str,
    search_results: List[Dict[str, Any]],
    agent_role_prompt: str,
    cfg: Config,
    parent_query: str,
    report_type: str,
    cost_callback: callable = None,
    retriever_names: List[str] = None,
    **kwargs
) -> List[str]:
    """
    Plan the research outline by generating sub-queries.

    Args:
        query: Original query
        search_results: Initial search results
        agent_role_prompt: Agent role prompt
        cfg: Configuration object
        parent_query: Parent query
        report_type: Report type
        cost_callback: Callback for cost calculation
        retriever_names: Names of the retrievers being used

    Returns:
        A list of sub-queries
    """
    # Handle the case where retriever_names is not provided
    if retriever_names is None:
        retriever_names = []
    
    # For MCP retrievers, we may want to skip sub-query generation
    # Check if MCP is the only retriever or one of multiple retrievers
    if retriever_names and ("mcp" in retriever_names or "MCPRetriever" in retriever_names):
        mcp_only = (len(retriever_names) == 1 and 
                   ("mcp" in retriever_names or "MCPRetriever" in retriever_names))
        
        if mcp_only:
            # If MCP is the only retriever, skip sub-query generation
            logger.info("Using MCP retriever only - skipping sub-query generation")
            # Return the original query to prevent additional search iterations
            return [query]
        else:
            # If MCP is one of multiple retrievers, generate sub-queries for the others
            logger.info("Using MCP with other retrievers - generating sub-queries for non-MCP retrievers")

    # Generate sub-queries for research outline
    sub_queries = await generate_sub_queries(
        query,
        parent_query,
        report_type,
        search_results,
        cfg,
        cost_callback,
        **kwargs
    )

    return sub_queries
