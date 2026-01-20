const Mutation = require("../../mutation");

/**
 * DODOperator is a mutation testing operator that targets the 'delete' operator in Solidity smart contracts.
 * 
 * **Purpose**:
 * This operator creates mutations by replacing occurrences of the `delete` operator with its operand. By doing this, it helps evaluate how removing the `delete` operation affects the behavior of the smart contract. Specifically, it tests whether the absence of the `delete` operator causes unintended side effects or issues in the contract's functionality.
 * 
 * **How It Works**:
 * 1. **Identifies Unary Operations**: It traverses the abstract syntax tree (AST) of the smart contract to find unary operations with the `delete` operator.
 * 2. **Generates Mutations**:
 *    - For each `delete` operation, it creates a mutation where the `delete` operator is replaced with the operand expression being deleted. This tests the impact of removing the `delete` operation.
 * 3. **Mutation Details**:
 *    - The mutation captures the start and end positions of the `delete` operator, the line numbers, the original code, and the modified code with the `delete` operator removed.
 * 
 * This script is useful for testing how the absence of the `delete` operator might impact the smart contract's behavior, ensuring that contracts handle deletion operations correctly.
 */

function DODOperator() {
  this.ID = "DOD";
  this.name = "delete-operator-deletion";
}

DODOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  visit({
    UnaryOperation: (node) => {
      if (node.operator === "delete") {
        const start = node.range[0];
        const end = node.range[1] + 1; // Include the end of the 'delete' operation
        const startLine = node.loc.start.line;
        const endLine = node.loc.end.line;
        const original = source.slice(start, end); // Extract the original code

        // Replace 'delete' with the operand expression
        const replacement = source.slice(node.subExpression.range[0], node.subExpression.range[1] + 1);
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
      }
    }
  });

  return mutations;
};

module.exports = DODOperator;
