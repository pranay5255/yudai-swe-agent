const Mutation = require("../../mutation");

/**
 * CBDOperator is a mutation testing operator that targets `try` statements with multiple `catch` clauses.
 * 
 * This script traverses the code to find `try` statements that have more than one `catch` clause. It generates mutations
 * by deleting each `catch` block one at a time. The mutations are as follows:
 * 
 * 1. For each `catch` clause in a `try` statement with more than one `catch` clause:
 *    - **Deletion**: The `catch` clause is removed from the `try` statement, leaving only the remaining `catch` clauses (if any).
 * 
 * The purpose of this operator is to test whether existing tests can detect issues caused by the absence of specific `catch` clauses
 * in exception handling blocks.
 */

function CBDOperator() {
  this.ID = "CBD";
  this.name = "catch-block-deletion";
}

CBDOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];
  
  // Visit all `try` statements in the code
  visit({
    TryStatement: (node) => {
      // Proceed only if the `try` statement has more than one `catch` clause
      if (node.catchClauses.length > 1) {
        var start, end;
        var lineStart, lineEnd;
        
        // Iterate through each `catch` clause
        node.catchClauses.forEach(c => {
          // Calculate the range and location for the `catch` clause
          start = c.range[0];
          end = c.range[1] + 1;  // Include the end of the `catch` clause in the range
          lineStart = c.loc.start.line;
          lineEnd = c.loc.end.line;
          const original = source.slice(start, end);
          const replacement = ""; // Replacement is an empty string to represent deletion

          // Create a mutation that represents the deletion of the `catch` clause
          mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, replacement, this.ID));
        });
      }
    }
  });

  return mutations;
};

module.exports = CBDOperator;
