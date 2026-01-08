const Mutation = require('../../mutation');

/**
 * HLRoperator is a mutation testing operator designed to mutate hexadecimal literals in Solidity smart contracts.
 * 
 * **Purpose**:
 * This operator tests the impact of replacing hexadecimal literals with their incremented and decremented values.
 * 
 * **How It Works**:
 * 1. **Identifies Hexadecimal Literals**: Searches for hexadecimal literals in the Solidity contract.
 * 2. **Generates Mutations**:
 *    - Replaces each hexadecimal literal with its incremented and decremented values.
 * 
 * **Mutation Details**:
 * - For each hexadecimal literal, create mutations by incrementing and decrementing the value.
 */

function HLRoperator() {
  this.ID = "HLR";
  this.name = "hexadecimal-literal-replacement";
}

HLRoperator.prototype.getMutations = function (file, source, visit) {
  const mutations = [];
  let prevRange;

  visit({
    HexLiteral: (node) => {
      // Avoid duplicate mutants
      if (prevRange != node.range) {
        if (node.value) {
          const start = node.range[0];
          const end = node.range[1] + 1;
          const startLine = node.loc.start.line;
          const endLine = node.loc.end.line;
          const original = source.slice(start, end);
          
          // Convert hex value to decimal
          let hexToDecimal = parseInt(node.value, 16);
          let hexToDecimalIncrement = (hexToDecimal + 1).toString(16);
          let hexToDecimalDecrement = (hexToDecimal - 1).toString(16);

          // Ensure even number of nibbles for hex values
          if (hexToDecimalIncrement.length % 2 !== 0) {
            hexToDecimalIncrement = "0" + hexToDecimalIncrement;
          }
          if (hexToDecimalDecrement.length % 2 !== 0) {
            hexToDecimalDecrement = "0" + hexToDecimalDecrement;
          }

          let replacement = original.replace(node.value, hexToDecimalIncrement);
          let replacement2 = original.replace(node.value, hexToDecimalDecrement);

          // Generate mutations
          if (hexToDecimal === 0) {
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
          } else {
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement2, this.ID));
          }
        }
      }
      prevRange = node.range;
    }
  });

  return mutations;
};

module.exports = HLRoperator;
