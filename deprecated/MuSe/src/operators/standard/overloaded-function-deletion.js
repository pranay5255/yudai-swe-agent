const Mutation = require('../../mutation');

/**
 * OLFDOperator is a mutation testing operator for deleting overloaded functions in Solidity smart contracts.
 * 
 * **Purpose**:
 * This operator helps identify issues by testing the impact of removing overloaded functions. It is useful for ensuring that the contract's behavior is robust and handles cases where overloaded functions are missing.
 * 
 * **How It Works**:
 * 1. **Identify All Functions**: Collect all functions in the contract.
 * 2. **Filter Overloaded Functions**: Identify functions with the same name but different signatures.
 * 3. **Generate Mutations**: Create mutations by removing these overloaded functions.
 * 
 * **Mutation Details**:
 * - Deletes functions that are overloaded and not marked as overridden.
 */

function OLFDOperator() {
  this.ID = "OLFD";
  this.name = "overloaded-function-deletion";
}

OLFDOperator.prototype.getMutations = function(file, source, visit) {

  const ID = this.ID;
  const mutations = [];
  var ranges = [];
  var contractFunctions = [];
  var overloadedFunctions = [];

  visitFunctions(mutate);

  function visitFunctions(callback) {
    // Visit and save all contract functions
    visit({
      FunctionDefinition: (node) => {
        if (!ranges.includes(node.range)) {
          if (!node.isConstructor && !node.isReceiveEther && !node.isFallback) {
            contractFunctions.push(node);
          }
        }
        ranges.push(node.range);
      }
    });
    callback();
  }

  // Mutate overloaded functions
  function mutate() {
    // Identify overloaded functions
    const lookup = contractFunctions.reduce((a, e) => {
      a[e.name] = ++a[e.name] || 0;
      return a;
    }, {});
    overloadedFunctions = contractFunctions.filter(e => lookup[e.name] > 1);

    overloadedFunctions.forEach(node => {
      // Overridden functions are not mutated by OLFD
      if (!node.override) {
        var start = node.range[0];
        var end = node.range[1] + 1;
        const startLine = node.loc.start.line;
        const endLine = node.loc.end.line; 
        const original = source.slice(start, end);
        const replacement = "";
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, ID));
      }
    });
  }

  return mutations;
};

module.exports = OLFDOperator;
