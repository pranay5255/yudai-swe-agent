const Mutation = require('../../mutation');

function REOperator() {
  this.ID = "RE";
  this.name = "reentrancy";
}

REOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];
  const mappings = new Set();

  visit({
    StateVariableDeclaration: (node) => {
      node.variables.forEach((variable) => {
        if (
          variable.typeName.type === "Mapping" &&
          variable.typeName.keyType.name === "address" &&
          variable.typeName.valueType.name &&
          (variable.typeName.valueType.name.includes("uint") ||
            variable.typeName.valueType.name.includes("bool"))
        ) {
          mappings.add(variable.name);
        }
      });
    }
  });

  function isMappingAssignment(stmt) {
    if (
      stmt.type !== "ExpressionStatement" ||
      stmt.expression.type !== "BinaryOperation" ||
      stmt.expression.operator === "+="
    ) return false;

    const left = stmt.expression.left;
    const right = stmt.expression.right;

    const isAddition = right.type === "BinaryOperation" && right.operator === "+";

    return (
      left.type === "IndexAccess" &&
      left.index &&
      left.index.type === "MemberAccess" &&
      left.index.memberName === "sender" &&
      mappings.has(left.base.name) &&
      !isAddition
    );
  }

function isExternalCall(stmt) {
  // Case 1: VariableDeclarationStatement con FunctionCall (anche tuple)
  if (
    stmt.type === "VariableDeclarationStatement" &&
    stmt.initialValue &&
    stmt.initialValue.type === "FunctionCall"
  ) {
    const expr = stmt.initialValue.expression;

    // Modern case con named args
    if (
      expr.type === "NameValueExpression" &&
      expr.expression &&
      expr.expression.type === "MemberAccess" &&
      expr.expression.memberName === "call" &&
      expr.expression.expression &&
      expr.expression.expression.type === "MemberAccess" &&
      expr.expression.expression.memberName === "sender"
    ) {
      return true;
    }

    // Caso classico .call.value(...)
    if (
      expr.type === "FunctionCall" &&
      expr.expression &&
      expr.expression.type === "MemberAccess" &&
      expr.expression.memberName === "value" &&
      expr.expression.expression &&
      expr.expression.expression.type === "MemberAccess" &&
      expr.expression.expression.memberName === "call" &&
      expr.expression.expression.expression &&
      expr.expression.expression.expression.type === "MemberAccess" &&
      expr.expression.expression.expression.memberName === "sender"
    ) {
      return true;
    }

    // Classic call directly (e.g., msg.sender.call(...))
    if (
      expr.type === "MemberAccess" &&
      expr.memberName === "call" &&
      expr.expression &&
      expr.expression.type === "MemberAccess" &&
      expr.expression.memberName === "sender"
    ) {
      return true;
    }
  }

  // Case 2: ExpressionStatement con FunctionCall (senza lvalue)
  if (
    stmt.type === "ExpressionStatement" &&
    stmt.expression &&
    stmt.expression.type === "FunctionCall"
  ) {
    const expr = stmt.expression.expression;

    // Named args
    if (
      expr.type === "NameValueExpression" &&
      expr.expression &&
      expr.expression.type === "MemberAccess" &&
      expr.expression.memberName === "call" &&
      expr.expression.expression &&
      expr.expression.expression.type === "MemberAccess" &&
      expr.expression.expression.memberName === "sender"
    ) {
      return true;
    }

    // .call(...)
    if (
      expr.type === "MemberAccess" &&
      expr.memberName === "call" &&
      expr.expression &&
      expr.expression.type === "MemberAccess" &&
      expr.expression.memberName === "sender"
    ) {
      return true;
    }

    // .call.value(...)
    if (
      expr.type === "FunctionCall" &&
      expr.expression &&
      expr.expression.type === "MemberAccess" &&
      expr.expression.memberName === "value" &&
      expr.expression.expression &&
      expr.expression.expression.type === "MemberAccess" &&
      expr.expression.expression.memberName === "call" &&
      expr.expression.expression.expression &&
      expr.expression.expression.expression.type === "MemberAccess" &&
      expr.expression.expression.expression.memberName === "sender"
    ) {
      return true;
    }
  }

  return false;
}

  function findRelevantStatements(statements) {
    let assignmentStmt = null;
    let callStmt = null;

    function recurse(stmts) {
      for (const stmt of stmts) {
        if (!assignmentStmt && isMappingAssignment(stmt)) {
          assignmentStmt = stmt;
        }

        if (assignmentStmt && !callStmt && isExternalCall(stmt)) {
          callStmt = stmt;
        }

        if (stmt.type === "IfStatement") {
          if (stmt.trueBody && stmt.trueBody.statements) {
            recurse(stmt.trueBody.statements);
          }
          if (stmt.falseBody && stmt.falseBody.statements) {
            recurse(stmt.falseBody.statements);
          }
        } else if (stmt.type === "Block" && stmt.statements) {
          recurse(stmt.statements);
        }

        if (assignmentStmt && callStmt) return;
      }
    }

    recurse(statements);
    return { assignmentStmt, callStmt };
  }

  visit({
    FunctionDefinition: (node) => {
      if (!node.body || !node.body.statements) return;

      const { assignmentStmt, callStmt } = findRelevantStatements(node.body.statements);

      if (assignmentStmt && callStmt) {
        const mutationStart = assignmentStmt.range[0];
        const mutationEnd = callStmt.range[1] + 1;

        const assignmentCode = source.slice(assignmentStmt.range[0], assignmentStmt.range[1] + 1);
        const callCode = source.slice(callStmt.range[0], callStmt.range[1] + 1);

        const startLine = assignmentStmt.loc.start.line;
        const endLine = callStmt.loc.end.line;

        const mutatedCode = callCode + "\n" + assignmentCode;

        mutations.push(
          new Mutation(
            file,
            mutationStart,
            mutationEnd,
            startLine,
            endLine,
            source.slice(mutationStart, mutationEnd),
            mutatedCode,
            this.ID
          )
        );
      }
    }
  });

  return mutations;
};

module.exports = REOperator;