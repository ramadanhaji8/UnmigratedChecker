# Gemini PDF-assistent

Et kommandolinjeværktøj, der analyserer store byggetekniske PDF-dokumenter (f.eks. bygningsreglementet og tekniske anvisninger) med Google Gemini. Hele PDF'en uploades direkte til Gemini og læses i modellens store kontekstvindue – der bruges ingen vektordatabase (ingen RAG). Svarene indeholder kildehenvisninger med sidetal, afsnit og tabelnumre.

## 1. Opret et virtuelt miljø

Åbn en terminal i denne mappe og kør:

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 2. Installér afhængigheder

```bash
pip install -r requirements.txt
```

## 3. Få en gratis API-nøgle

1. Gå til [Google AI Studio](https://aistudio.google.com/app/apikey) og log ind med din Google-konto.
2. Klik på **Create API key** og kopiér nøglen.
3. Kopiér `.env.example` til en ny fil med navnet `.env`:
   - Windows: `copy .env.example .env`
   - macOS / Linux: `cp .env.example .env`
4. Åbn `.env` og erstat `your_api_key_here` med din nøgle.

`.env` er udelukket fra git, så din nøgle ikke bliver delt ved en fejl.

## 4. Kør scriptet

```bash
python ask_pdf.py sti/til/dokument.pdf "Dit spørgsmål her"
```

Eksempel:

```bash
python ask_pdf.py BR18.pdf "Hvad er kravet til mindste taghældning for tegltag?"
```

Scriptet bruger `gemini-2.5-flash` som standard. Vil du bruge en anden Gemini-model (f.eks. den mere grundige `gemini-2.5-pro`), kan du angive den med `--model`:

```bash
python ask_pdf.py BR18.pdf "Dit spørgsmål" --model gemini-2.5-pro
```

Statusbeskeder skrives til stderr, så du kan gemme selve svaret i en fil:

```bash
python ask_pdf.py BR18.pdf "Dit spørgsmål" > svar.txt
```

Den uploadede fil slettes automatisk fra Gemini, når svaret er modtaget.
