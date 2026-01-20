const Mutation = require('../../mutation');

/**
 * ILROperator is a mutation testing operator designed to mutate integer literals in Solidity smart contracts.
 * 
 * **Purpose**:
 * This operator tests the impact of replacing integer literals with different values.
 * 
 * **How It Works**:
 * 1. **Identifies Integer Literals**: Searches for integer literals in the contract's code.
 * 2. **Generates Mutations**:
 *    - Replaces integer literals with values incremented and decremented by 1.
 *    - Replaces specific values (like 0 and 1) with alternative values.
 * 
 * **Mutation Details**:
 * - For each integer literal, create mutations by altering the integer values.
 */

function ILROperator() {
  this.ID = "ILR";
  this.name = "integer-literal-replacement";
}

ILROperator.prototype.getMutations = function (file, source, visit) {

  const ID = this.ID;
  const mutations = [];
  const ranges = []; //Visited node ranges

  // Visit tuple expressions that are arrays
  visit({
    TupleExpression: (node) => {
      if (node.isArray) {
        if (node.components[0] && node.components[0].type == "NumberLiteral") {
          if (!ranges.includes(node.range)) {
            // Mark the range of the array and its components
            ranges.push(node.range);
            // Mutate the first component and exclude subsequent components
            mutateIntegerLiteral(node.components[0]);
            node.components.forEach(e => {
              ranges.push(e.range);
            });
          }
        }
      }
    }
  });

  // Visit number literals
  visit({
    NumberLiteral: (node) => {
      if (!ranges.includes(node.range)) {
        ranges.push(node.range);
        mutateIntegerLiteral(node);
      }
    }
  });

  /**
   * Function to mutate integer literals
   * @param {Object} node - The AST node representing the integer literal
   */
  function mutateIntegerLiteral(node) {
    let value = node.number.toString();
    // Check if it is a hexadecimal value
    if (!value.match(/^0x[0-9a-f]+$/i)) {
      if (node.number % 1 === 0) { // Check if it's an integer
        let subdenomination = "";
        let start = node.range[0];
        let end = node.range[1] + 1;
        const startLine = node.loc.start.line;
        const endLine = node.loc.end.line;
        let original = source.slice(start, end);

        if (node.subdenomination) {
          subdenomination = " " + node.subdenomination;
        }

        // Special case for the number 1
        if (node.number == 1) {
          let sliced = source.slice(node.range[0] - 1, node.range[0]);
          if (sliced === "-") {
            start = node.range[0] - 1;
            original = source.slice(start, end);
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, "0" + subdenomination, ID));
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, "-2" + subdenomination, ID));
          } else {
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, "0" + subdenomination, ID));
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, "2" + subdenomination, ID));
          }
        } else if (node.number == 0) { // Special case for the number 0
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, "1" + subdenomination, ID));
        } else { // General case for other integers
          let num = Number(node.number);
          let inc;
          let dec;

          if (num < Number.MAX_SAFE_INTEGER) {
            inc = num + 1;
            dec = num - 1;
          }

          mutations.push(new Mutation(file, start, end, startLine, endLine, original, dec + subdenomination, ID));
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, inc + subdenomination, ID));
        }
      }
    }
  }

  return mutations;
};

module.exports = ILROperator;
