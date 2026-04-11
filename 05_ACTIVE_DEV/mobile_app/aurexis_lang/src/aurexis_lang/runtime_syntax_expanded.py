def evaluate_ir_expanded(ir):
    ops = [child.op for child in getattr(ir, "children", [])]
    return {
        "status": "syntax_expanded_stub",
        "program_ops": ops,
        "statement_count": len(ops),
    }
