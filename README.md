# AuroHear — Web-Based Hearing Asymmetry Screening Tool

> **Project Context:** Preliminary Hearing Asymmetry Screening Platform using Adaptive Audiometry[cite: 1]  
> **Original Team Repository:** [nishnarudkar/AuroHear--Web-Based-Hearing-Asymmetry-Screening-Tool](https://github.com/nishnarudkar/AuroHear--Web-Based-Hearing-Asymmetry-Screening-Tool)

---

# AuroHear

**Professional web-based hearing asymmetry screening platform**

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green?style=flat-square&logo=flask)](https://flask.palletsprojects.com)
[![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-yellow?style=flat-square&logo=javascript)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)

AuroHear provides preliminary audiometric testing at standard frequencies (250-5000 Hz) using adaptive algorithms to identify significant interaural differences (≥20 dB) that may indicate hearing asymmetries.

> **Medical Disclaimer**: This is a screening tool only - not a diagnostic instrument. All results require professional audiological interpretation.

## Live Demo

>  **Experience the platform:**  
> **[https://aurohear-website.onrender.com](https://aurohear-website.onrender.com)**


## Features

- **Adaptive Audiometry**: Hughson-Westlake algorithms with catch trials for reliability assessment
- **Standard Testing**: Complete frequency range (250-5000 Hz) with precise dB HL mapping
- **User Management**: Supabase authentication with privacy-focused guest mode
- **Interactive Reports**: Professional PDF/PNG exports with audiogram visualizations
- **Response Analytics**: Reliability scoring and interaural difference analysis
- **NLP Reliability Module**: Automated feedback analysis for platform improvement
- **Modern Interface**: Responsive design with accessibility compliance

## Interface Preview

![Test in Progress](Screenshots/aurohear%20test%20in%20progress.png)
*Active hearing test with real-time response tracking*

![Test Results](Screenshots/aurohear%20demo%20test%20results.png)
*Detailed audiometric results with frequency visualization*

![Feedback Analysis](Screenshots/aurohear%20demo%20analysis.png)
*NLP-powered feedback analysis and reliability scoring*

![User History](Screenshots/AuroHear%20Testhistory.png)
*Comprehensive testing history and trend tracking*

![Profile Management](Screenshots/AuroHear%20User%20Profile.png)
*User profile settings and preference management*

![Feedback Form](Screenshots/aurohear%20feedback%20form.png)
*Integrated feedback collection for continuous improvement*

## Quick Start

### Prerequisites
- Python 3.10+ with pip
- Node.js 16+ (for frontend dependencies)
- Supabase account (for authentication and database)

### Installation

```bash
# Clone and setup
git clone <repository-url>
cd aurohear
python -m venv venv

# Activate environment
venv\Scripts\activate          # Windows
source venv/bin/activate       # Unix/Mac

# Install dependencies
pip install -r requirements.txt
npm install

# Configure environment
cp .env.example .env
# Edit .env with your Supabase credentials

# Initialize database
python backend/migrate_db.py

# Run application
python app.py
```

### Environment Configuration

Create `.env` file with:
```env
DATABASE_URL=your_supabase_database_url
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
FLASK_ENV=development
```

## Project Structure

```
aurohear/
├── app.py                     # Main Flask application
├── requirements.txt           # Python dependencies
├── package.json              # Node.js dependencies
│
├── backend/                   # Backend Python modules
│   ├── config.py             # Configuration management
│   ├── database.py           # Database initialization
│   ├── models/               # Database models
│   ├── routes/               # Flask route blueprints
│   ├── utils/                # Utility functions
│   └── nlp_engine/           # NLP processing module
│
├── static/                   # Frontend assets
│   ├── styles.css           # Application styles
│   └── script.js            # Application JavaScript
│
├── templates/               # HTML templates
│   └── index.html          # Main application template
│
├── tests/                  # Test suite
├── docs/                   # Documentation
└── .github/               # GitHub workflows
```

For detailed structure documentation, see [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md).

## Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test suites
python tests/test_nlp_integration.py
python tests/test_feedback_nlp_integration.py

# Test NLP pipeline
python backend/nlp_engine/store_results.py
```

## Documentation

### Core Platform
- **[PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)** - Complete architecture guide
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment guide
- **[SUPABASE_NLP_SETUP.md](docs/SUPABASE_NLP_SETUP.md)** - Database setup for NLP features

### NLP Reliability Module
- **[NLP_RELIABILITY_MODULE.md](docs/NLP_RELIABILITY_MODULE.md)** - Complete module documentation
  - System purpose and objectives
  - Data flow architecture
  - Database schema design
  - Ethical constraints and safeguards
  - Future expansion roadmap
- **[NLP_ARCHITECTURE_DIAGRAM.md](docs/NLP_ARCHITECTURE_DIAGRAM.md)** - Visual system architecture

## Technical Specifications

### Audio Processing
- **Sample Rate**: 44.1 kHz, 16-bit stereo
- **Frequency Range**: 250-5000 Hz (standard audiometric frequencies)
- **Algorithm**: Modified Hughson-Westlake with catch trials
- **Reliability**: Response consistency scoring with catch trial validation

### NLP Reliability Module
- **Purpose**: Automated feedback analysis for platform improvement
- **Models**: DistilBERT (sentiment), RoBERTa (emotions), custom rules (issues)
- **Processing**: Real-time analysis with Supabase storage
- **Ethics**: Complete separation from audiometric results - no clinical influence
- **Privacy**: Anonymous analysis, aggregated insights only

### Performance
- **Test Duration**: 8-12 minutes complete assessment
- **Browser Support**: Chrome 80+, Firefox 75+, Safari 13+, Edge 80+
- **Accuracy**: ±5 dB compared to clinical audiometry in controlled settings

## Deployment

### Development
```bash
python app.py              # Development server
python backend/migrate_db.py  # Database setup
```

### Production
```bash
# Docker deployment
docker build -t aurohear .
docker run -p 10000:10000 aurohear

# Or direct deployment
gunicorn app:app --bind 0.0.0.0:10000
```

Required environment variables:
- `DATABASE_URL`
- `SUPABASE_URL` 
- `SUPABASE_KEY`
- `SUPABASE_SERVICE_ROLE_KEY` (Required for NLP Insight storage)

## Future Enhancements & Research Roadmap

While the current version of AuroHear delivers a complete and functional hearing screening platform with integrated NLP-based reliability analysis, the system has been intentionally designed with a clear path for future growth. The following enhancements outline the planned evolution of the project as additional data and user interactions are collected.

### 1. Dataset Expansion & Longitudinal Analysis

As AuroHear continues to be used, the accumulation of feedback and behavioral data will enable deeper statistical analysis of:

- Session reliability trends
- Recurring user-reported issues
- Long-term changes in system performance and user experience

This growing dataset will support more robust validation of the NLP reliability framework.

### 2. System Health & Reliability Dashboard

A future administrative interface will visualize insights derived from `test_nlp_insights`, including:

- Overall system reliability scores
- Sentiment distribution across sessions
- Frequency of detected issues (e.g., noise, audibility, delay)
- Recent low-confidence test sessions

This dashboard will allow developers and researchers to proactively identify potential system weaknesses and user-experience bottlenecks.

### 3. Intelligent User Experience Feedback Loop

Using real-time NLP insights, AuroHear will introduce adaptive user interactions such as:

- Immediate support prompts after negative feedback
- Contextual guidance for low-confidence sessions
- Personalized recommendations for improved testing conditions

These mechanisms will enhance usability while maintaining strict separation from clinical decision logic.

### 4. Advanced Reliability Modeling

With sufficient data volume, future versions will refine the reliability scoring framework through:

- Improved weighting of behavioral and linguistic indicators
- Supervised learning from clinician-validated sessions
- Cross-analysis between environmental factors and user experience

This will further strengthen the interpretability and trustworthiness of screening outcomes.

### 5. Research & Open Dataset Contribution

An anonymized reliability dataset derived from aggregated NLP and behavioral insights may be released for research purposes, enabling external validation, benchmarking, and continued innovation in human-centered screening systems.

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/name`)
3. Follow project structure guidelines in [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)
4. Add tests and update documentation
5. Submit pull request

### Development Guidelines
- Follow PEP 8 (Python) and ESLint (JavaScript) standards
- Maintain clear separation between backend and frontend
- Use proper imports from backend modules
- Add comprehensive tests for new features

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

**AuroHear** - Professional hearing screening platform for educational and preliminary assessment purposes only. Always consult healthcare professionals for medical advice.
