from typing import List

from .parser_stub import Token, ASTNode

def parse_block(tokens: List[Token]) -> ASTNode:
    body = []
    current = []
    in_block = False

    for token in tokens:
        if token.token_type == "block_start":
            in_block = True
            if current:
                body.append(ASTNode(node_type="Preamble", value={"count": len(current)}))
                current = []
        elif token.token_type == "block_end":
            if current:
                body.append(ASTNode(node_type="StatementStub", value={"count": len(current)}))
                current = []
            in_block = False
        else:
            current.append(token)

    if current:
        body.append(ASTNode(node_type="StatementStub", value={"count": len(current)}))

    return ASTNode(node_type="Block", children=body, value={"in_block": in_block})

def parse_control(tokens: List[Token]) -> ASTNode:
    if not tokens:
        return ASTNode(node_type="EmptyControl")
    head = tokens[0]
    if head.token_type == "control":
        return ASTNode(
            node_type="Control",
            value={"keyword": head.value},
            children=[ASTNode(node_type="Tail", value={"count": len(tokens) - 1})],
        )
    return ASTNode(node_type="NonControl", value={"count": len(tokens)})

def parse_program_with_scope(tokens: List[Token]) -> ASTNode:
    program = ASTNode(node_type="Program")
    if any(t.token_type in {"block_start", "block_end"} for t in tokens):
        program.children.append(parse_block(tokens))
    elif tokens and tokens[0].token_type == "control":
        program.children.append(parse_control(tokens))
    else:
        program.children.append(ASTNode(node_type="FlatProgram", value={"count": len(tokens)}))
    return program
