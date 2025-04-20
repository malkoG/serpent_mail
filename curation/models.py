from django.db import models
import requests
import readtime
from langchain.chains.summarize import load_summarize_chain
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders.web_base import WebBaseLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
import os


class Article(models.Model):
    url = models.URLField(unique=True, max_length=2048, help_text="The unique URL of the article.")
    title = models.CharField(max_length=512, blank=True, help_text="Article title (can be fetched automatically or entered manually).")
    summary = models.TextField(blank=True, help_text="AI-generated summary of the article.")
    summary_ko = models.TextField(blank=True, help_text="Korean translation of the summary (via OpenAI).")
    reading_time_minutes = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Estimated reading time in minutes (based on full article content)."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title or self.url
        
    def calculate_reading_time(self, full_text: str):
        """Calculates reading time based on the provided text."""
        if full_text:
            try:
                result = readtime.of_text(full_text)
                self.reading_time_minutes = result.minutes
            except Exception as e:
                print(f"Error calculating reading time for article {self.id}: {e}")
                self.reading_time_minutes = None # Set to None on calculation error
        else:
            self.reading_time_minutes = None

    def fetch_and_summarize(self) -> str:
        """
        Fetches content, calculates reading time on full text, generates summary,
        translates summary, and saves all results.
        """
        if not self.url:
            return "Error: No URL provided."

        full_content_text = "" # Variable to hold the full text

        try:
            # --- Step 1: Load Content ---
            loader = WebBaseLoader(self.url)
            docs = loader.load() # Load documents

            if not docs or not docs[0].page_content:
                return "Error: No content could be loaded from the URL."

            full_content_text = docs[0].page_content # Store full text

            if not self.title and docs[0].metadata.get('title'):
                self.title = docs[0].metadata.get('title')

            # --- Step 2: Calculate Reading Time (on full content) ---
            self.calculate_reading_time(full_content_text) # Call updated method

            # --- Step 3: Generate Summary ---
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                self.save(update_fields=['title', 'reading_time_minutes', 'updated_at']) # Save what we have
                return "Error: OpenAI API key not found. Title/Reading Time saved."

            llm_summarize = ChatOpenAI(api_key=api_key, model_name="gpt-4o", temperature=0.2)
            chain_summarize = load_summarize_chain(llm_summarize, chain_type="map_reduce")
            summary_result = chain_summarize.invoke(docs)
            summary_text = summary_result.get('output_text', '')

            if not summary_text:
                self.summary = ""
                self.summary_ko = ""
                self.save(update_fields=['title', 'summary', 'summary_ko', 'reading_time_minutes', 'updated_at'])
                return "Error extracting summary. Other details saved."

            self.summary = summary_text # Set summary

            # --- Step 4: Translate Summary (immediately after generation) ---
            translation_status = self.translate_summary_to_korean() # Call translation
            print(f"Translation status for article {self.id}: {translation_status}")
            translation_failed = "Error" in translation_status

            # --- Step 5: Final Save ---
            self.save(update_fields=[ # Save everything together
                'title',
                'summary',
                'summary_ko', # Make sure ko summary is saved
                'reading_time_minutes',
                'updated_at'
            ])

            final_message = "Fetch, Read Time, Summary completed."
            final_message += " Translation failed." if translation_failed else " Translation completed."
            return final_message

        except requests.exceptions.RequestException as e:
             return f"Error fetching URL: {str(e)}"
        except ImportError as e:
            return f"Error with required libraries: {str(e)}"
        except Exception as e:
             print(f"Unexpected error during fetch/summarize/translate for {self.id}: {e}")
             # Optionally try saving minimal info on unexpected error:
             # self.save(update_fields=['title', 'reading_time_minutes', 'summary', 'summary_ko', 'updated_at'])
             return f"Unexpected error processing article: {str(e)}"
            
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
