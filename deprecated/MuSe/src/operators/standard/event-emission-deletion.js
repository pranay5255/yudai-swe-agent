const Mutation = require('../../mutation');

/**
 * EEDOperator is a mutation testing operator designed to test the impact of removing event emissions from Solidity smart contracts.
 * 
 * **Purpose**:
 * This operator generates mutations by commenting out event emission statements. It helps to assess how the absence of event emissions affects the smart contract's behavior and monitoring.
 * 
 * **How It Works**:
 * 1. **Identifies Emit Statements**: The operator looks for `EmitStatement` nodes in the abstract syntax tree (AST) of the smart contract.
 * 2. **Generates Mutations**:
 *    - **Replace Emit Statements**: Each found `EmitStatement` is replaced with a commented-out version of the same statement.
 * 
 * This script is useful for evaluating how the removal of event emissions affects the functionality and traceability of smart contracts.
 */

function EEDOperator() {
  this.ID = "EED";
  this.name = "event-emission-deletion";
}

EEDOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  visit({
    EmitStatement: (node) => {
      // Determine the range and location of the EmitStatement
      const start = node.range[0];
      const end = node.range[1] + 1;
      const startLine = node.loc.start.line;
      const endLine = node.loc.end.line;
      
      // Extract the original source code of the EmitStatement
      const original = source.slice(start, end);
      
      // Prepare the replacement code which comments out the EmitStatement
      const replacement = "/* " + original + " */";

      // Create a Mutation object and add it to the mutations array
      mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
    }
  });

  return mutations;
};

module.exports = EEDOperator;
