# InterpAscend - Professional Translation & Terminology Platform

InterpAscend is a Django-based web application designed for professional interpreters, translators, and language professionals. It provides instant access to specialized terminology across multiple domains including medical, legal, financial, immigration, and government sectors.

## 🚀 Features

### Multi-Domain Terminology Database
- **Medical Terms**: Medications, diagnoses, and MeSH (Medical Subject Headings) terms
- **Financial Terms**: Banking, insurance, and financial terminology
- **Legal/Immigration Terms**: Immigration law and government agency terminology
- **Language Learning**: L2 and L3 terms with sample sentences and definitions

### Advanced Search & Translation
- **Intelligent Language Detection**: Automatically detects English or Spanish input
- **Multiple Search Types**: Exact match, contains, or starts with search options
- **AI-Powered Fallback**: OpenAI GPT integration for terms not in local database
- **Bilingual Support**: Comprehensive English ⟷ Spanish translations

### Audio Pronunciation
- **Text-to-Speech Integration**: Audio pronunciation files for proper term pronunciation
- **Bilingual Audio**: Separate audio files for English and Spanish pronunciations

### Professional Features
- **Specialized Glossaries**: Purpose-built for professional interpreting contexts
- **Context-Aware Translations**: Maintains professional terminology standards
- **Sample Sentences**: Real-world usage examples for complex terms

## 📋 Requirements

- Python 3.8+  
- Django 5.2.1  
- Docker & Docker Hub account  
- OpenAI API Key  
- (Optional) GCP Project & Secret Manager for production secrets

## 🛠️ Installation

## 🛠️ Quickstart (Local)

### 1. Clone & enter project
```bash
git clone https://github.com/mariano-fu/InterpAscend.git
cd InterpAscend
```

### 2. Build & Run with Docker (Development)

This section helps you run InterpAscend locally using Docker. Make sure you have [Docker](https://www.docker.com/get-started) installed.

#### 🛠️ Build the Docker image:
```bash
# Build image with a placeholder key for static collection
docker build -t nanofu97/interpascend:latest .

# Run container and expose it on http://localhost:8080
docker run --rm \
  -p 8080:8080 \
  -e PORT=8080 \
  -e DJANGO_SECRET_KEY="$DJANGO_SECRET_KEY" \
  -e DJANGO_DEBUG=true \
  -e DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1" \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  nanofu97/interpascend:latest
```
Visit http://localhost:8080/admin/ (should redirect to login)

### 3. Environment variables (dev)
```bash
export DJANGO_SECRET_KEY="$(python -c 'from django.core.management.utils import get_random_secret_key; print(_ )')"
export DJANGO_DEBUG=true
export DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1"
export OPENAI_API_KEY="your-openai-key"
```

---

## 🐳 CI/CD & Deployment

### 1. Tag & push image to Docker Hub
```bash
docker build -t nanofu97/interpascend:vX .
docker push nanofu97/interpascend:vX
```

### 2. Deploy to Cloud Run
1. In GCP Console go to **Cloud Run → Services → interpascend**.  
2. Click **Edit & deploy new revision**.  
3. Set **Container image URL** to `docker.io/nanofu97/interpascend:vX`.  
4. Under **Security → Secrets**, inject:
   - `DJANGO_SECRET_KEY` (from Secret Manager)  
   - `OPENAI_API_KEY` (from Secret Manager)  
   - `DJANGO_DEBUG=false`  
   - `DJANGO_ALLOWED_HOSTS=interpascend-<id>.<region>.run.app`  
5. Click **Deploy** and verify:
```bash
curl -I https://<service-url>/admin/
# Expect: 302 Found → /admin/login/
```

> **Note:** Production secrets should live in Secret Manager and be injected at runtime—never bake them into the image.

---

## ⚙️ Database & Data Import

Migrate and import CSV data via management commands:
```bash
python manage.py migrate
python manage.py import_medications
python manage.py import_diagnoses
python manage.py import_mesh_terms
python manage.py import_financial_glossary
python manage.py import_government_agency_glossary
python manage.py import_immigration_glossary
python manage.py import_l2_glossary
python manage.py import_l3_glossary
```
> Optionally, enable **django-import-export** in the Admin UI for CSV imports.

---

## 📁 Project Structure
```
InterpAscend/
├── interpascend1_1/          # Django project
│   ├── settings.py           # config (env-driven)
│   ├── urls.py
│   └── wsgi.py
├── terminology/              # Django app
│   ├── models.py
│   ├── views.py
│   ├── llm_utils.py
│   ├── forms.py
│   ├── urls.py
│   ├── templates/
│   └── management/commands/  # import_*.py scripts
├── Dockerfile
├── manage.py
└── README.md
```

## 🎯 Usage

### Basic Translation
1. Navigate to the main translation interface
2. Enter a term in English or Spanish
3. Select search type (exact, contains, starts with)
4. View results from multiple terminology databases
5. Click on terms for detailed information and pronunciation

### Search Types
- **Exact Match**: Find terms that match exactly
- **Contains**: Find terms containing the search query
- **Starts With**: Find terms beginning with the search query

### Audio Pronunciation
- Click the audio icons next to terms to hear proper pronunciation
- Separate audio available for English and Spanish terms

## 📊 Database Models

### Core Models
- **[`Medication`](terminology/models.py:3)**: Medical medications with FDA descriptions
- **[`Diagnosis`](terminology/models.py:11)**: Medical diagnoses and conditions
- **[`MeSHTerm`](terminology/models.py:18)**: Medical Subject Headings
- **[`FinancialTerm`](terminology/models.py:24)**: Financial and insurance terminology
- **[`GovernmentAgencyTerm`](terminology/models.py:30)**: Government agencies and departments
- **[`ImmigrationTerm`](terminology/models.py:39)**: Immigration law terminology
- **[`L2Term`](terminology/models.py:53)**: Language learning terms (Level 2)
- **[`L3Term`](terminology/models.py:71)**: Language learning terms (Level 3)
- **[`MedicareGlossaryTerm`](terminology/models.py:91)**: Medicare glossary terms

## 🔧 Configuration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

- see the LICENSE file for details.

## 🆘 Support

For support, please open an issue in the GitHub repository or contact the development team.

## 🔮 Future Enhancements

- Additional language pairs beyond English/Spanish
- Real-time collaborative translation features
- Advanced terminology management tools
- Mobile application development
- Integration with professional CAT tools

---

## About the Creator
InterpAscend was built by a bilingual interpreter turned developer, focused on tools that empower new interpreters in medical, legal and service settings.

**InterpAscend** - Empowering professional interpreters and translators with instant access to specialized terminology.



