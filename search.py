from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

TOKEN_REGEX = re.compile(r'\(|\)|\bAND\b|\bOR\b|\bNOT\b|"[^"]+"|\w+', re.IGNORECASE)


@dataclass
class QueryToken:
    value: str
    type: str


def tokenize(query: str) -> list[QueryToken]:
    tokens: list[QueryToken] = []
    for match in TOKEN_REGEX.findall(query):
        upper = match.upper()
        if upper in {"AND", "OR", "NOT", "(", ")"}:
            tokens.append(QueryToken(upper, upper))
        else:
            cleaned = match.strip('"')
            tokens.append(QueryToken(cleaned, "TERM"))
    return tokens


def to_postfix(tokens: list[QueryToken]) -> list[QueryToken]:
    precedence = {"NOT": 3, "AND": 2, "OR": 1}
    output: list[QueryToken] = []
    stack: list[QueryToken] = []
    for token in tokens:
        if token.type == "TERM":
            output.append(token)
        elif token.type in {"AND", "OR", "NOT"}:
            while stack and stack[-1].type in precedence and precedence[stack[-1].type] >= precedence[token.type]:
                output.append(stack.pop())
            stack.append(token)
        elif token.type == "(":
            stack.append(token)
        elif token.type == ")":
            while stack and stack[-1].type != "(":
                output.append(stack.pop())
            if stack and stack[-1].type == "(":
                stack.pop()
    while stack:
        output.append(stack.pop())
    return output


def evaluate_postfix(postfix: list[QueryToken], text: str) -> bool:
    stack: list[bool] = []
    text_lower = text.lower()
    for token in postfix:
        if token.type == "TERM":
            stack.append(token.value.lower() in text_lower)
        elif token.type == "NOT":
            if stack:
                stack.append(not stack.pop())
        elif token.type in {"AND", "OR"}:
            if len(stack) >= 2:
                right = stack.pop()
                left = stack.pop()
                stack.append(left and right if token.type == "AND" else left or right)
    return stack[-1] if stack else False


def search_resumes(query: str, resumes: Iterable[tuple[int, str, str]]) -> list[tuple[int, str]]:
    tokens = tokenize(query)
    postfix = to_postfix(tokens)
    results = []
    for resume_id, name, text in resumes:
        if evaluate_postfix(postfix, text):
            results.append((resume_id, name))
    return results
