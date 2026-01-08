const Mutation = require('../../mutation');

/**
 * PKDOperator is a mutation testing operator for deleting the `payable` keyword from function signatures in Solidity smart contracts.
 * 
 * **Purpose**:
 * This operator helps identify issues by testing the impact of removing the `payable` keyword from functions. It is useful for ensuring that the contract handles cases where functions that are supposed to accept Ether (because they are `payable`) do not work as intended when the `payable` keyword is removed.
 * 
 * **How It Works**:
 * 1. **Identify All Payable Functions**: Collect all functions marked as `payable`.
 * 2. **Generate Mutations**: Create mutations by removing the `payable` keyword from these function signatures.
 * 
 * **Mutation Details**:
 * - Removes the `payable` keyword from function signatures where it appears.
 */

function PKDOperator() {
  this.ID = "PKD";
  this.name = "payable-keyword-deletion";
}

PKDOperator.prototype.getMutations = function (file, source, visit) {
  const mutations = [];

  visit({
    FunctionDefinition: (node) => {
      if (node.stateMutability === "payable" && !node.isReceiveEther && !node.isVirtual && !node.override) {
        let start, end, startLine, endLine;
        if (node.body) {
          start = node.range[0];
          end = node.body.range[0];
          startLine = node.loc.start.line;
          endLine = node.body.loc.start.line;
        } else {
          start = node.range[0];
          end = node.range[1];
          startLine = node.loc.start.line;
          endLine = node.loc.end.line;
        }
        const original = source.slice(start, end); // function signature
        const replacement = original.replace(/payable(?![\s\S]*payable)/, ''); // remove the last occurrence of 'payable'
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
      }
    }
  });
  
  return mutations;
};

module.exports = PKDOperator;
