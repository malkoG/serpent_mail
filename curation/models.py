from django.db import models
import requests
import readtime
from langchain.chains.summarize import load_summarize_chain
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os


class Article(models.Model):
    url = models.URLField(unique=True, max_length=2048, help_text="The unique URL of the article.")
    title = models.CharField(max_length=512, blank=True, help_text="Article title (can be fetched automatically or entered manually).")
    summary = models.TextField(blank=True, help_text="AI-generated summary of the article.")
    summary_ko = models.TextField(blank=True, help_text="Korean translation of the summary (via OpenAI).")
    reading_time_minutes = models.PositiveIntegerField(null=True, blank=True, help_text="Estimated reading time in minutes.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title or self.url
        
    def calculate_reading_time(self):
        """Calculates reading time based on the summary."""
        if self.summary:
            result = readtime.of_text(self.summary)
            self.reading_time_minutes = result.minutes
        else:
            self.reading_time_minutes = None

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
            
            # Calculate reading time
            self.calculate_reading_time()
            
            self.save(update_fields=['title', 'summary', 'reading_time_minutes', 'updated_at'])
            
            return "Summary generated and saved successfully."
            
        except requests.exceptions.RequestException as e:
            self.reading_time_minutes = None
            return f"Error fetching URL: {str(e)}"
        except ImportError as e:
            self.reading_time_minutes = None
            return f"Error with required libraries: {str(e)}"
        except Exception as e:
            self.reading_time_minutes = None
            self.save(update_fields=['reading_time_minutes'])
            return f"Unexpected error: {str(e)}"
            
    def translate_summary_to_korean(self):
        """Translates the summary to Korean using the OpenAI API via Langchain."""
        if not self.summary:
            self.summary_ko = ""
            return "No summary to translate."

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "Error: OpenAI API key not found."

        try:
            llm = ChatOpenAI(api_key=api_key, model_name="gpt-4o", temperature=0.2)
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful assistant that translates English text to Korean."),
                ("user", "Please translate the following English text accurately to Korean:\n\n{english_text}")
            ])
            parser = StrOutputParser()
            chain = prompt | llm | parser

            translated_text = chain.invoke({"english_text": self.summary})

            self.summary_ko = translated_text.strip() if translated_text else ""
            self.save(update_fields=['summary_ko', 'updated_at'])
            return "Summary translated successfully using OpenAI."

        except Exception as e:
            print(f"Error translating article {self.id} using OpenAI: {e}")
            self.summary_ko = "" # Clear on error
            self.save(update_fields=['summary_ko', 'updated_at'])
            return f"Error during OpenAI translation: {str(e)[:150]}"
