from django.db import models
import requests
from langchain.chains.summarize import load_summarize_chain
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import WebBaseLoader
import os


class Article(models.Model):
    url = models.URLField(unique=True, max_length=2048, help_text="The unique URL of the article.")
    title = models.CharField(max_length=512, blank=True, help_text="Article title (can be fetched automatically or entered manually).")
    summary = models.TextField(blank=True, help_text="AI-generated summary of the article.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title or self.url

    def fetch_and_summarize(self) -> str:
        """
        Fetch content from the article URL, generate a summary using OpenAI,
        and save the summary to the model.
        
        Returns:
            str: Success message or error description
        """
        # Check if URL exists
        if not self.url:
            return "Error: No URL provided."
        
        try:
            # Load content from URL
            loader = WebBaseLoader(self.url)
            docs = loader.load()
            
            if not docs:
                return "Error: No content could be loaded from the URL."
            
            # Try to populate title if it's blank
            if not self.title and docs[0].metadata.get('title'):
                self.title = docs[0].metadata.get('title')
            
            # Get OpenAI API key
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return "Error: OpenAI API key not found in environment variables."
            
            # Initialize LLM
            llm = ChatOpenAI(
                api_key=api_key,
                model_name="gpt-4o",
                temperature=0.2
            )
            
            # Create and run summarization chain
            chain = load_summarize_chain(llm, chain_type="map_reduce")
            result = chain.invoke(docs)
            
            # Extract and save summary
            summary_text = result.get('output_text', 'Error extracting summary.')
            self.summary = summary_text
            self.save(update_fields=['title', 'summary', 'updated_at'])
            
            return "Summary generated and saved successfully."
            
        except requests.exceptions.RequestException as e:
            return f"Error fetching URL: {str(e)}"
        except ImportError as e:
            return f"Error with required libraries: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"
