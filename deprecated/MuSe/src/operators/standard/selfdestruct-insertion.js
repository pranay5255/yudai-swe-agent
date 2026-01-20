const Mutation = require('../../mutation');

/**
 * SFIOperator is a mutation testing operator designed to insert `selfdestruct` function calls into Solidity smart contracts.
 * 
 * **Purpose**:
 * The operator aims to test how the contract behaves with an added `selfdestruct` call within the function bodies. The `selfdestruct` function is used to destroy the contract and send its remaining funds to a specified address. By inserting this call into functions, the mutation helps to verify if the contract handles unexpected contract destruction scenarios correctly.
 * 
 * **How It Works**:
 * 1. **Identify Existing `selfdestruct` Calls**: The script checks if there are any `selfdestruct` function calls within the contract functions.
 * 2. **Insert `selfdestruct` Calls**: For each function, it inserts a `selfdestruct` call at the beginning of the function body.
 * 3. **Create Mutation Instances**: These mutations are then added to a list for further analysis and testing.
 */

function SFIOperator() {
  this.ID = "SFI";
  this.name = "selfdestruct-function-insertion";
}

SFIOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  visit({
    FunctionDefinition: (funcNode) => {
      // Iterate through function calls within the function body
      visit({
        FunctionCall: (node) => {
          // Check if the function call is `selfdestruct`
          if (node.expression.name === "selfdestruct") {
            // Create a string for the selfdestruct call
            const selfDestruct = source.slice(node.range[0], node.range[1] + 1) + ";";

            // Ensure the selfdestruct call is within the function range
            if (node.range[0] >= funcNode.range[0] && node.range[1] <= funcNode.range[1]) {
              const start = funcNode.body.range[0];
              const end = funcNode.body.range[0] + 1;
              const startLine = funcNode.body.loc.start.line;
              const endLine = funcNode.body.loc.end.line;
              // Capture the original start of the function body
              const original = source.slice(start, end);  
              // Create a replacement that includes the selfdestruct call
              const replacement = original + " " + selfDestruct;
              // Add the mutation to the list
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
            }
          }
        }
      });
    }
  });

  return mutations;
}

module.exports = SFIOperator;
