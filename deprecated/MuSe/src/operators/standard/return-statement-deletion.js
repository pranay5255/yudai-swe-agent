const Mutation = require('../../mutation');

/**
 * RSDoperator is a mutation testing operator for deleting return statements by commenting them out.
 * 
 * **Purpose**:
 * This operator helps identify issues by testing the impact of removing return statements from functions. It is useful for ensuring that the contract behaves correctly even when return statements are omitted.
 * 
 * **How It Works**:
 * 1. **Identify Return Statements**: Collect all return statements in the contract.
 * 2. **Generate Mutations**: Create mutations by commenting out these return statements.
 * 
 * **Mutation Details**:
 * - Comments out return statements.
 */

function RSDoperator() {
  this.ID = "RSD";
  this.name = "return-statement-deletion";
}

RSDoperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  visit({
    ReturnStatement: (node) => {
      const start = node.range[0];
      const end = node.range[1] + 1;
      const startLine = node.loc.start.line;
      const endLine = node.loc.end.line;

      const original = source.slice(start, end);
      const replacement = "/* " + original + " */"; // Comment out the return statement

      mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
    }
  });

  return mutations;
};

module.exports = RSDoperator;
