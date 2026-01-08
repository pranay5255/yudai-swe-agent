const Mutation = require('../../mutation');

/**
 * LSCOperator is a mutation testing operator designed to mutate loop condition statements in Solidity smart contracts.
 * 
 * **Purpose**:
 * This operator tests the impact of changing loop condition statements to always true or always false.
 * 
 * **How It Works**:
 * 1. **Identifies Loop Statements**: Searches for for-loops and while-loops in the contract's code.
 * 2. **Generates Mutations**:
 *    - Replaces loop condition expressions with `true`.
 *    - Replaces loop condition expressions with `false`.
 * 
 * **Mutation Details**:
 * - For each loop condition expression, create mutations by replacing it with `true` and `false`.
 */

function LSCOperator() {
  this.ID = "LSC";
  this.name = "loop-statement-change";
}

LSCOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  // Visit for-loop statements
  visit({
    ForStatement: (node) => {
      const start = node.conditionExpression.range[0];
      const end = node.conditionExpression.range[1] + 1;
      const startLine = node.conditionExpression.loc.start.line;
      const endLine = node.conditionExpression.loc.end.line;
      const original = source.slice(start, end);

      // Create mutations by replacing condition with true and false
      mutations.push(new Mutation(file, start, end, startLine, endLine, original, "true", this.ID));
      mutations.push(new Mutation(file, start, end, startLine, endLine, original, "false", this.ID));
    }
  });

  // Visit while-loop statements
  visit({
    WhileStatement: (node) => {
      const start = node.condition.range[0];
      const end = node.condition.range[1] + 1;
      const startLine = node.condition.loc.start.line;
      const endLine = node.condition.loc.end.line;
      const original = source.slice(start, end);

      // Create mutations by replacing condition with true and false
      mutations.push(new Mutation(file, start, end, startLine, endLine, original, "true", this.ID));
      mutations.push(new Mutation(file, start, end, startLine, endLine, original, "false", this.ID));
    }
  });

  return mutations;
};

module.exports = LSCOperator;
