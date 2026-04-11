from .ir import IRNode

def ast_to_ir_expanded(ast) -> IRNode:
    root = IRNode(op="program")
    for child in getattr(ast, "children", []):
        if child.node_type == "Assignment":
            root.children.append(IRNode(op="assign", args={"kind": "assignment"}))
        elif child.node_type == "BinaryExpression":
            root.children.append(IRNode(op="binary_expr", args={"kind": "expression"}))
        else:
            root.children.append(IRNode(op="unknown_stmt", args={"kind": child.node_type}))
    return root
