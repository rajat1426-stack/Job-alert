import pandas as pd
import requests
import json
from bs4 import BeautifulSoup
from jobspy import scrape_jobs
from openai import OpenAI

client = OpenAI(api_key="YOUR_OPENAI_API_KEY")
WEBHOOK_URL = "https://discord.com/api/webhooks/1551965226683867226/AgkGzBLs3ydhnXSUr_MDpVg-vlC9gV8QibX-2Saznoosw764F3XzBXnOaxdll7451jok"

def scrape_tum_hiwi():
    """Scrapes the TUM Schwarzes Brett for student assistant positions."""
    url = "https://portal.mytum.de/schwarzesbrett/hiwi_stellen/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    tum_jobs = []
    # TUM job posts utilize 'NewsArticle' in their URL structure
    for link in soup.find_all('a', href=True):
        if 'NewsArticle' in link['href']:
            title = link.text.strip()
            if title:
                tum_jobs.append({
                    "title": title,
                    "company": "TUM / Academic Chair",
                    "description": "TUM HiWi/Student Assistant position. Full details in URL.",
                    "job_url": link['href'],
                    "source": "TUM HiWi"
                })
    return pd.DataFrame(tum_jobs).drop_duplicates(subset=['job_url'])

def scrape_commercial_boards():
    """Scrapes LinkedIn and Indeed for part-time/Werkstudent roles."""
    return scrape_jobs(
        site_name=["linkedin", "indeed"],
        search_term="GIS OR Remote Sensing OR Earth Observation OR Geoinformatics",
        location="Munich, Germany",
        job_type="parttime", 
        results_wanted=20,
        hours_old=48 
    )

def evaluate_and_dispatch():
    print("Scraping TUM HiWi board...")
    tum_df = scrape_tum_hiwi()
    
    print("Scraping LinkedIn and Indeed...")
    commercial_df = scrape_commercial_boards()
    
    # Merge all retrieved jobs
    all_jobs = pd.concat([commercial_df, tum_df], ignore_index=True)
    
    for index, row in all_jobs.iterrows():
        # Inject your specific profile data for the LLM evaluation
        eval_prompt = f"""
        Job Title: {row['title']} at {row['company']}
        Source: {row.get('source', 'Commercial Board')}
        Job Description Preview: {str(row['description'])[:2000]}
        
        Candidate Profile:
        - Education: MSc Land Management & Geospatial Science (TUM), MTech SVNIT, B.Plan SPA Bhopal[cite: 1, 2].
        - Experience: TUM Student Research Assistant (Microclimatic data, HOBO sensors, ENVI-met), Federal Bank, GMRC[cite: 1, 2].
        - Technical Stack: Python (GeoPandas, Pandas, Scikit learn), ArcGIS, QGIS, PyTorch, Earth Engine, Sentinel-2, NDVi/NDBI[cite: 1, 2].
        - Projects: CNN-based brownfield detection (Munich), Seasonal Snow Cover Change (Sentinel-2, Austrian Alps), Seismic Risk Mapping (HAZUS)[cite: 1, 2].
        - Languages: English C1, German A1 (Actively Learning)[cite: 1, 2].
        
        Task:
        1. Score the job (0) if it explicitly demands fluent/native German (C1/C2) or is entirely unrelated to GIS/Urban Planning/Data.
        2. Score the match (0-100) based on alignment with the candidate's geospatial and programming stack.
        3. If score >= 75, draft a concise, targeted 3-paragraph cover letter mapping the job's needs to the candidate's specific GIS projects and TUM background.
        
        Return exactly in JSON: {{"score": 85, "rationale": "...", "cover_letter": "..."}}
        """

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": eval_prompt}]
            )
            result = json.loads(response.choices[0].message.content)
            
            if result['score'] >= 75:
                # Dispatch alert to webhook
                msg = (f"**New High-Match Role: {row['title']} @ {row['company']}**\n"
                       f"**Match Score:** {result['score']}/100\n"
                       f"**Rationale:** {result['rationale']}\n"
                       f"**Apply Link:** {row['job_url']}")
                
                requests.post(WEBHOOK_URL, json={"content": msg})
                
                # Save auto-generated cover letter locally
                safe_title = "".join([c for c in str(row['title']) if c.isalnum()]).rstrip()
                with open(f"CoverLetter_{safe_title}.txt", "w", encoding="utf-8") as f:
                    f.write(result['cover_letter'])
                    
        except Exception as e:
            print(f"Error evaluating {row['title']}: {e}")

if __name__ == "__main__":
    evaluate_and_dispatch()