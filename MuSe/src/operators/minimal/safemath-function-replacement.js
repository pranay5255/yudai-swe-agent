const Mutation = require("../../mutation");

/**
 * The SFROperator class performs mutation testing by replacing SafeMath function calls with different SafeMath functions.
 * This mutation is used to test the robustness and correctness of smart contracts that use the SafeMath library for safe mathematical operations.
 * The script first checks whether the SafeMath library is imported. If it is, it looks for function calls to SafeMath operations and swaps them with other SafeMath functions.
 * This process helps identify potential issues or vulnerabilities that may arise from changing arithmetic operations within the contract.
 */

function SFROperator() {
  this.ID = "SFR";
  this.name = "safemath-function-replacement";
}

/**
 * Generates mutations by replacing SafeMath function calls with different SafeMath functions.
 * 
 * @param {string} file - The name of the file being mutated.
 * @param {string} source - The source code of the file.
 * @param {function} visit - A function to visit nodes in the source code's abstract syntax tree (AST).
 * @returns {Array} - An array of Mutation objects representing the generated mutations.
 */
SFROperator.prototype.getMutations = function (file, source, visit) {
  const mutations = [];
  var isUsingSafeMath = false;

  // Check if the contract imports the SafeMath library
  visit({
    ImportDirective: (node) => {
      if (node.path.includes('SafeMath'))
        isUsingSafeMath = true;
    }
  });

  // If SafeMath is used, replace SafeMath function calls with different functions
  if (isUsingSafeMath) {
    visit({
      MemberAccess: (node) => {
        const start = node.range[0];
        const end = node.range[1] + 1;
        const startLine = node.loc.start.line;
        const endLine = node.loc.end.line;
        const original = source.slice(start, end);

        var replacement;

        // Replace SafeMath functions with different SafeMath functions
        switch (node.memberName) {
          case 'add':
            replacement = original.replace('add', 'sub');
            break;
          case 'sub':
            replacement = original.replace('sub', 'add');
            break;
          case 'mul':
            replacement = original.replace('mul', 'div');
            break;
          case 'div':
            replacement = original.replace('div', 'mul');
            break;
          case 'mod':
            replacement = original.replace('mod', 'mul');
            break;
        }

        // If a replacement is found, create a mutation
        if (replacement) {
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
        }
      }
    });
  }

  return mutations;
};

module.exports = SFROperator;
