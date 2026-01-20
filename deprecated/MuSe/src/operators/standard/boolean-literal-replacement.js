const Mutation = require("../../mutation");

/**
 * BLROperator is a mutation testing operator for replacing boolean literals.
 * This script traverses the code to find boolean literal nodes (i.e., `true` or `false`) and generates mutations by swapping their values. For instance, `true` is replaced with `false` and vice versa. This helps in testing whether the code can handle changes in boolean values and whether existing tests are capable of detecting errors introduced by these changes.
 * The operator ensures that each boolean literal node is only mutated once to avoid duplicate mutations.
 */

function BLROperator() {
  this.ID = "BLR";
  this.name = "boolean-literal-replacement";
}

BLROperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];
  var prevRange; // To keep track of the previously visited node's range to avoid duplicates

  visit({
    BooleanLiteral: (node) => {
      const start = node.range[0];
      const end = node.range[1] + 1;
      const startLine = node.loc.start.line;
      const endLine = node.loc.end.line;
      const original = source.slice(start, end);

      // Ensure that the same node is not mutated more than once
      if (prevRange != node.range) {
        if (node.value) {
          // Replace 'true' with 'false'
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, "false", this.ID));
        } else {
          // Replace 'false' with 'true'
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, "true", this.ID));
        }
      }
      prevRange = node.range;
    }
  });

  return mutations;
};

module.exports = BLROperator;
