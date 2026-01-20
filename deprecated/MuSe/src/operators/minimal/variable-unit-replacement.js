const Mutation = require("../../mutation");

/**
 * The VUROperator class performs mutation testing by replacing units of measurement within numerical literals.
 * This includes both Ethereum-related units (e.g., wei, gwei, ether) and time units (e.g., seconds, minutes, hours).
 * The purpose of this script is to test how changing these units impacts the behavior of smart contracts.
 * It helps to identify potential issues arising from unit conversion errors or unexpected behaviors due to unit changes.
 */

function VUROperator() {
  this.ID = "VUR";
  this.name = "variable-unit-replacement";
}

/**
 * Generates mutations by replacing units of measurement in numerical literals.
 * 
 * @param {string} file - The name of the file being mutated.
 * @param {string} source - The source code of the file.
 * @param {function} visit - A function to visit nodes in the source code's abstract syntax tree (AST).
 * @returns {Array} - An array of Mutation objects representing the generated mutations.
 */
VUROperator.prototype.getMutations = function (file, source, visit) {
  const mutations = [];
  var prevRange;

  // Visit each NumberLiteral node in the source code
  visit({
    NumberLiteral: (node) => {
      if (node.subdenomination) {
        // Ensure that the current node's range is not the same as the previous node's range
        if (prevRange != node.range) {
          const start = node.range[0];
          const end = node.range[1] + 1;
          const lineStart = node.loc.start.line;
          const lineEnd = node.loc.end.line;
          const original = source.slice(start, end);
          let replacement;

          // Replace units of measurement with different units
          switch (node.subdenomination) {
            // Ethereum Units Replacement
            case "wei":
              replacement = original.replace("wei", "ether");
              break;
            case 'gwei':
              replacement = original.replace('gwei', 'wei');
              break;
            case 'finney':
              replacement = original.replace('finney', 'wei');
              break;
            case 'szabo':
              replacement = original.replace('szabo', 'wei');
              break;
            case "ether":
              replacement = original.replace("ether", "wei");
              break;
            // Time Units Replacement
            case "seconds":
              replacement = original.replace("seconds", "minutes");
              break;
            case "minutes":
              replacement = original.replace("minutes", "hours");
              break;
            case "hours":
              replacement = original.replace("hours", "days");
              break;
            case "days":
              replacement = original.replace("days", "weeks");
              break;
            case "weeks":
              replacement = original.replace("weeks", "seconds");
              break;
            case "years":
              replacement = original.replace("years", "seconds");
          }

          // Create a Mutation object if a replacement is made
          if (replacement) {
            mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, replacement, this.ID));
          }
        }
        prevRange = node.range;
      }
    }
  });

  return mutations;
};

module.exports = VUROperator;
