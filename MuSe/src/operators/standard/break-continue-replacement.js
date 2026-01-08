const Mutation = require("../../mutation");

/**
 * BCRDOperator is a mutation testing operator that targets `break` and `continue` statements.
 * 
 * This script traverses the code to find `break` and `continue` statements and generates mutations in the following ways:
 * 
 * 1. Replaces `break` statements with `continue` statements.
 * 2. Deletes `break` statements entirely.
 * 3. Replaces `continue` statements with `break` statements.
 * 4. Deletes `continue` statements entirely.
 * 
 * The purpose of this operator is to evaluate if existing tests can detect issues caused by changes in control flow statements.
 */

function BCRDOperator() {
  this.ID = "BCRD";
  this.name = "break-continue-replacement-deletion";
}

BCRDOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  // Visit and mutate `break` statements
  visit({
    BreakStatement: (node) => {
      var start = node.range[0];
      var end = node.range[1];
      const startLine = node.loc.start.line;
      const endLine = node.loc.end.line;
      const original = source.slice(start, end);

      // Replace `break` with `continue`
      mutations.push(new Mutation(file, start, end, startLine, endLine, original, "continue", this.ID));
      // Delete `break`
      mutations.push(new Mutation(file, start, end + 1, startLine, endLine, original, "", this.ID));
    }
  });

  // Visit and mutate `continue` statements
  visit({
    ContinueStatement: (node) => {
      var start = node.range[0];
      var end = node.range[1];
      const startLine = node.loc.start.line;
      const endLine = node.loc.end.line;
      const original = source.slice(start, end);

      // Replace `continue` with `break`
      mutations.push(new Mutation(file, start, end, startLine, endLine, original, "break", this.ID));
      // Delete `continue`
      mutations.push(new Mutation(file, start, end + 1, startLine, endLine, original, "", this.ID));
    }
  });

  return mutations;
};

module.exports = BCRDOperator;
