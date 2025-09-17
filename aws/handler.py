import json
import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import string
import spacy
from nltk.stem import RSLPStemmer
from dataclasses import dataclass
import nltk

nltk.download('rslp')

# ============================
# MODELOS DE DADOS
# ============================
@dataclass
class Comentario:
    autor: str
    nota: float
    conteudo: str
    criticas: int = None
    seguidores: int = None

@dataclass
class Filme:
    nome: str
    nota: float
    resumo: str
    url: str = None
    comentarios: list[Comentario] = None

@dataclass
class FilmeProcessado(Filme):
    resumo_tokens: list[str] = None
    resumo_stem: list[str] = None
    resumo_lema: list[str] = None

@dataclass
class ComentarioProcessado(Comentario):
    conteudo_tokens: list[str] = None
    conteudo_stem: list[str] = None
    conteudo_lema: list[str] = None


# ============================
# FUNÇÕES DE EXTRAÇÃO
# ============================
URL = "https://www.adorocinema.com/filmes/melhores/adorocinema/?page="

def extrair_filmes(paginas=2):
    filmes = []
    for i in range(1, paginas + 1):
        response = requests.get(URL + str(i))
        soup = BeautifulSoup(response.content, 'html.parser')
        links = soup.find_all('a', class_='meta-title-link')
        for link in links:
            url = 'https://www.adorocinema.com' + link.get('href')
            resp = requests.get(url + 'criticas-adorocinema/')
            sp = BeautifulSoup(resp.content, 'html.parser')
            resumo = " ".join([d.getText() for d in sp.find_all('p', class_='bo-p')])
            title = sp.find('div', class_='title').getText()
            grade = sp.find('span', class_='note').getText()
            filmes.append(Filme(
                re.sub('\\s\\s+', '', title.replace('\n', '')),
                float(grade.replace(',', '.')),
                resumo,
                url,
                []
            ))
    return filmes

def extrair_comentarios(url_filme, max_comentarios=40):
    comentarios = []
    url = url_filme + "/criticas/espectadores/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    cards = soup.find_all(class_='review-card')
    for card in cards[:max_comentarios]:
        try:
            nome = card.find('div', class_='meta-title').find('span').text.strip()
            nota_elem = card.find(class_='stareval-note')
            nota = float(nota_elem.text.strip().replace(',', '.')) if nota_elem else 0.0
            conteudo_elem = card.find(class_='review-card-content')
            conteudo = conteudo_elem.text.strip() if conteudo_elem else ""
            comentarios.append(Comentario(autor=nome, nota=nota, conteudo=conteudo))
        except Exception as e:
            print(f"Erro comentário: {e}")
    return comentarios


# ============================
# FUNÇÕES DE SALVAR
# ============================
def salvar_filmes_csv(filmes):
    base_path = "/tmp/filmes_csv"
    os.makedirs(base_path, exist_ok=True)

    df_filmes = pd.DataFrame([{
        "nome": f.nome,
        "nota": f.nota,
        "resumo": f.resumo
    } for f in filmes])

    df_comentarios = pd.DataFrame([{
        "nome_filme": f.nome,
        "autor_comentario": c.autor,
        "nota_comentario": c.nota,
        "conteudo_comentario": c.conteudo
    } for f in filmes for c in (f.comentarios or [])])

    filmes_path = os.path.join(base_path, "filmes.csv")
    comentarios_path = os.path.join(base_path, "comentarios.csv")

    df_filmes.to_csv(filmes_path, index=False, encoding="utf-8-sig")
    df_comentarios.to_csv(comentarios_path, index=False, encoding="utf-8-sig")

    return filmes_path, comentarios_path


# ============================
# PROCESSAMENTO DE TEXTO
# ============================
nlp = spacy.load("pt_core_news_md")
stemmer = RSLPStemmer()

def processar_texto(texto):
    doc = nlp(texto)
    tokens_filtrados = [
        t.text.lower() for t in doc
        if t.text.lower() not in nlp.Defaults.stop_words and t.text not in string.punctuation
    ]
    stemmed = [stemmer.stem(t) for t in tokens_filtrados]
    lemas = [t.lemma_ for t in doc]
    return tokens_filtrados, stemmed, lemas


# ============================
# HANDLER LAMBDA
# ============================
def run_job(event=None, context=None):
    filmes = extrair_filmes()
    for f in filmes:
        f.comentarios = extrair_comentarios(f.url)

    filmes_csv, comentarios_csv = salvar_filmes_csv(filmes)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "mensagem": "Extração concluída",
            "filmes_csv": filmes_csv,
            "comentarios_csv": comentarios_csv
        })
    }
