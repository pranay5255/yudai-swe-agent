const Mutation = require('../../mutation');

/**
 * SFDOperator is a mutation testing operator that focuses on removing the `selfdestruct` function calls from Solidity smart contracts.
 * 
 * **Purpose**:
 * The operator aims to test the contract's resilience by mutating any `selfdestruct` function calls within the contract. The `selfdestruct` function in Solidity is used to destroy the contract and send its remaining funds to a specified address. By removing these calls, the mutation helps to verify how the contract behaves when its self-destruction capability is disabled.
 * 
 * **How It Works**:
 * 1. **Identify Selfdestruct Calls**: The script scans for instances of the `selfdestruct` function call in the contract.
 * 2. **Generate Mutations**: For each `selfdestruct` call found, it creates a mutation by replacing the function call with a comment that contains the original code. This effectively "deletes" the call while preserving the code for reference.
 * 3. **Create Mutation Instances**: These mutations are then added to a list for further analysis and testing.
 */

function SFDOperator() {
  this.ID = "SFD";
  this.name = "selfdestruct-function-deletion";
}

SFDOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  // Visit and identify `selfdestruct` function calls
  visit({
    FunctionCall: (node) => {
      if (node.expression.name === "selfdestruct") {
        const start = node.range[0];
        // Find the end of the `selfdestruct` call by locating the delimiter
        const temp = source.slice(start);
        const delimiter = temp.indexOf(";");
        const end = start + delimiter + 1;
        const startLine = node.loc.start.line;
        const endLine = node.loc.end.line;
        const original = source.slice(start, end);
        // Create a replacement that comments out the original `selfdestruct` call
        const replacement = "/* " + original + " */";

        // Add the mutation to the list
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
      }
    }
  });

  return mutations;
}

module.exports = SFDOperator;
