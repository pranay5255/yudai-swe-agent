const Mutation = require("../../mutation");

/**
 * CSCOperator is a mutation testing operator that focuses on modifying conditional statements, specifically `if` statements.
 * 
 * This script generates mutations by altering the condition of `if` statements and removing `else` clauses in certain scenarios:
 * 
 * 1. **Changing Conditions**: For each `if` statement:
 *    - It creates mutations where the `if` condition is replaced with `true`.
 *    - It creates additional mutations where the `if` condition is replaced with `false`.
 * 
 * 2. **Removing `else` Clauses**: If the `if` statement has an `else` clause:
 *    - It removes the entire `else` block to test how the code behaves without it.
 * 
 * The purpose of this operator is to assess the impact of condition and `else` block modifications on the code's functionality and robustness.
 */

function CSCOperator() {
  this.ID = "CSC";
  this.name = "conditional-statement-change";
}

CSCOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  visit({
    IfStatement: (node) => {
      // Mutation for changing the `if` condition to `true`
      var start = node.condition.range[0];
      var end = node.condition.range[1] + 1; // Include the end of the condition
      var lineStart = node.condition.loc.start.line;
      var lineEnd = node.condition.loc.end.line;
      var original = source.slice(start, end);
      mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, "true", this.ID));

      // Mutation for changing the `if` condition to `false`
      mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, "false", this.ID));

      // Mutation for removing the `else` body, if it exists
      if (node.falseBody && !node.falseBody.trueBody) { // Check if `else` body is the last part of the `if` statement
        start = node.trueBody.range[1] + 1;
        end = node.falseBody.range[1] + 1; // Include the end of the `else` body
        lineStart = node.trueBody.loc.start.line;
        lineEnd = node.falseBody.loc.end.line;
        original = source.slice(start, end);
        var replacement = ""; // Replacement is an empty string to represent deletion
        mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, replacement, this.ID));
      }
    }
  });

  return mutations;
};

module.exports = CSCOperator;
