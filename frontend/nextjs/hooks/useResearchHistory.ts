import { useState, useEffect } from 'react';
import { ResearchHistoryItem, Data } from '../types/data';

export const useResearchHistory = () => {
  const [history, setHistory] = useState<ResearchHistoryItem[]>([]);
  
  // Load history from localStorage on initial render
  useEffect(() => {
    const storedHistory = localStorage.getItem('researchHistory');
    console.log('🔍 Loading research history from localStorage:', storedHistory ? `${JSON.parse(storedHistory).length} items` : 'none found');
    if (storedHistory) {
      try {
        const parsedHistory = JSON.parse(storedHistory);
        setHistory(parsedHistory);
        console.log('✅ Research history loaded successfully:', parsedHistory.length, 'items');
      } catch (error) {
        console.error('❌ Error parsing research history:', error);
        // If there's an error parsing, reset the history
        localStorage.removeItem('researchHistory');
      }
    } else {
      console.log('📝 No existing research history found');
    }
  }, []);

  // Save research to history
  const saveResearch = (question: string, answer: string, orderedData: Data[]) => {
    console.log('💾 saveResearch called with:', { 
      question: question?.substring(0, 50) + '...', 
      answerLength: answer?.length,
      orderedDataLength: orderedData?.length 
    });
    
    const newItem: ResearchHistoryItem = {
      id: Date.now().toString(),
      question,
      answer,
      timestamp: Date.now(),
      orderedData,
    };

    // Use functional update to ensure we have the latest history
    setHistory(prevHistory => {
      const updatedHistory = [newItem, ...prevHistory];
      
      try {
        localStorage.setItem('researchHistory', JSON.stringify(updatedHistory));
        console.log('✅ Research saved to localStorage. Total items:', updatedHistory.length);
        
        // Verify the save worked
        const verification = localStorage.getItem('researchHistory');
        if (verification) {
          const parsed = JSON.parse(verification);
          console.log('✅ Save verification successful:', parsed.length, 'items in storage');
        }
      } catch (error) {
        console.error('❌ Error saving to localStorage:', error);
      }
      
      return updatedHistory;
    });
    
    return newItem.id;
  };

  // Get a specific research item by ID
  const getResearchById = (id: string) => {
    return history.find(item => item.id === id);
  };

  // Delete a research item
  const deleteResearch = (id: string) => {
    setHistory(prevHistory => {
      const updatedHistory = prevHistory.filter(item => item.id !== id);
      localStorage.setItem('researchHistory', JSON.stringify(updatedHistory));
      return updatedHistory;
    });
  };

  // Clear all history
  const clearHistory = () => {
    setHistory([]);
    localStorage.removeItem('researchHistory');
  };

  return {
    history,
    saveResearch,
    getResearchById,
    deleteResearch,
    clearHistory,
  };
}; 