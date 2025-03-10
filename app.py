import json
from flask import Flask, render_template, request, send_file
from openai import OpenAI
import pdfkit
import os
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)

# Ensure wkhtmltopdf is installed (Windows path example)
PDF_CONFIG = pdfkit.configuration(wkhtmltopdf="C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe")

universal_sections=dict()

def generate_resume(name, job_title, skills, experience, education, certifications, projects):
    # Convert comma-separated skills to bullet points
    skills_list = "\n- " + "\n- ".join(skills.split(",")) if skills else ""

    prompt = f"""
    Generate a well-structured, ATS-friendly resume for {name}, applying for a {job_title} role.

    **Rules:**
    - Format the resume with clear sections (Professional Summary, Skills, Experience, Education, Certifications, Projects).
    - Use bullet points for Skills & Experience.
    - Do NOT add placeholders like '[Company Name]', '[Month, Year]'. Use only user inputs.
    - Do NOT include address, phone number, or email—keep them as user-input fields.

    ---
    **{name}**

    **Professional Summary**
    - Provide a concise 2-3 sentence summary based on the job title and skills.

    **Technical Skills**
    {skills_list}

    **Professional Experience**
    {experience}

    **Education**
    {education}

    **Certifications**
    {certifications}

    **Projects**
    {projects}
    ---
    """

    # ✅ Correct OpenAI API request
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=700
    )

    resume_text = response.choices[0].message.content

    # **Pre-Process Sections for Jinja**
    sections = extract_sections(resume_text)
    universal_sections=sections

    return sections


def extract_sections(resume_text):
    """ Extracts different sections from the resume and returns them as a dictionary """
    sections = {
        "summary": "",
        "skills": "",
        "experience": "",
        "education": "",
        "certifications": "",
        "projects": ""
    }

    parts = resume_text.split("\n\n")  # Split by double newlines

    current_section = None
    for part in parts:
        if "**Professional Summary**" in part:
            current_section = "summary"
        elif "**Technical Skills**" in part:
            current_section = "skills"
        elif "**Professional Experience**" in part:
            current_section = "experience"
        elif "**Education**" in part:
            current_section = "education"
        elif "**Certifications**" in part:
            current_section = "certifications"
        elif "**Projects**" in part:
            current_section = "projects"
        
        if current_section:
            sections[current_section] += part.replace("**" + current_section.replace("_", " ").title() + "**", "").strip() + "\n"
    return sections

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form["name"]
        job_title = request.form["job_title"]
        skills = request.form["skills"]
        experience = request.form["experience"]
        education = request.form.get("education", "")
        certifications = request.form.get("certifications", "")
        projects = request.form.get("projects", "")

        resume = generate_resume(name, job_title, skills, experience, education, certifications, projects)

        return render_template("resume.html", resume=resume, name=name)

    return render_template("index.html", resume={})


@app.route("/download", methods=["POST"])
def download_pdf():
    lineChanger='\n'
    """ Generates a properly formatted PDF matching the on-screen resume. """

    # ✅ Extract the resume JSON string from the form
    raw_resume_data = request.form.get("resume", "{}")
    resume_sections=json.loads(raw_resume_data.replace("'", '"'))
    resume_sections=request.form

    # ✅ Function to ensure correct line breaks in PDF
    def format_text(text):
        return text.replace("\n", "<br>") if text else ""  # Ensure empty text does not return "N/A"

    # ✅ Create properly formatted HTML for the PDF
    html_resume = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Resume</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
                padding: 10px;
                line-height: 1.6;
            }}
            h2 {{
                text-align: center;
                text-transform: uppercase;
                border-bottom: 2px solid black;
                padding-bottom: 5px;
                margin-bottom: 20px;
            }}
            h3 {{
                border-bottom: 1px solid #007bff;
                padding-bottom: 5px;
                margin-bottom: 10px;
            }}
            ul {{
                margin: 0;
                padding-left: 20px;
            }}
            li {{
                margin-bottom: 5px;
            }}
            .section {{
                margin-bottom: 20px;
            }}
        </style>
    </head>
    <body>
        <h2>{resume_sections['name']}</h2>

        <div class="section">
            <h3>Professional Summary</h3>
            <p>{format_text(resume_sections['summary'])}</p>
        </div>

        <div class="section">
            <h3>Technical Skills</h3>
            <ul>
                {''.join([f"<li>{skill.strip()}</li>" for skill in resume_sections['skills'].split(lineChanger) if skill.strip()])}
            </ul>
        </div>

        <div class="section">
            <h3>Professional Experience</h3>
            <p>{format_text(resume_sections['experience'])}</p>
        </div>

        <div class="section">
            <h3>Education</h3>
            <p>{format_text(resume_sections['education'])}</p>
        </div>

        <div class="section">
            <h3>Certifications</h3>
            <p>{format_text(resume_sections['certifications'])}</p>
        </div>

        <div class="section">
            <h3>Projects</h3>
            <p>{format_text(resume_sections['projects'])}</p>
        </div>

    </body>
    </html>
    """

    # ✅ Generate PDF with properly formatted content
    pdfkit.from_string(html_resume, "resume.pdf", configuration=PDF_CONFIG)

    return send_file("resume.pdf", as_attachment=True)







if __name__ == "__main__":
    app.run(debug=True)
