from typing import List

from .parser_stub import Token, ASTNode

def parse_statement(tokens: List[Token]) -> ASTNode:
    # assignment
    if len(tokens) >= 3 and tokens[0].token_type == "identifier" and tokens[1].value == "=":
        return ASTNode(
            node_type="Assignment",
            children=[
                ASTNode(node_type="Identifier", value={"name": tokens[0].value}),
                ASTNode(node_type="Value", value={"value": tokens[2].value}),
            ],
        )

    # binary expression
    if len(tokens) >= 3 and tokens[1].token_type == "operator":
        return ASTNode(
            node_type="BinaryExpression",
            children=[
                ASTNode(node_type="Left", value={"value": tokens[0].value}),
                ASTNode(node_type="Operator", value={"value": tokens[1].value}),
                ASTNode(node_type="Right", value={"value": tokens[2].value}),
            ],
        )

    return ASTNode(node_type="UnknownStatement", value={"count": len(tokens)})

def split_statements(tokens: List[Token]):
    current = []
    groups = []
    for token in tokens:
        if token.token_type == "delimiter" and token.value == ";":
            if current:
                groups.append(current)
                current = []
        else:
            current.append(token)
    if current:
        groups.append(current)
    return groups

def parse_program(tokens: List[Token]) -> ASTNode:
    program = ASTNode(node_type="Program")
    for group in split_statements(tokens):
        program.children.append(parse_statement(group))
    return program
