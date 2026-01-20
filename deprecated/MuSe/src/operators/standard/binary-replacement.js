const Mutation = require('../../mutation');

/**
 * BOROperator is a mutation testing operator for replacing binary operators.
 * This script identifies binary operations in the code and generates mutations by replacing the original operators with various other operators. The purpose is to test whether existing tests can detect errors introduced by these changes.
 * For instance, if the original operator is `+`, the script will create mutations where `+` is replaced with `-` (subtraction), `*` (multiplication), `/` (division), `**` (exponentiation), and `%` (modulus), among others. This helps to assess the robustness of the code against different binary operations.
 */

function BOROperator() {
  this.ID = "BOR";
  this.name = "binary-operator-replacement";
}

BOROperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];
  var ranges = []; // To keep track of visited node ranges

  visit({
    BinaryOperation: (node) => {
      // Ensure the node has not been visited before
      if (!ranges.includes(node.range)) {
        ranges.push(node.range);

        // Determine the range of the binary operation
        const start = node.left.range[1] + 1;
        const end = node.right.range[0];
        const startLine = node.left.loc.end.line;
        const endLine = node.right.loc.start.line;
        const original = source.slice(start, end);

        // Variables to hold different replacement operators
        let replacement, replacement2, replacement3, replacement4, replacement5;

        // Determine replacements based on the current operator
        switch (node.operator) {
          // Arithmetic operators
          case '+':
            replacement = original.replace('+', '-');
            replacement2 = original.replace('+', '*');
            replacement3 = original.replace('+', '/');
            replacement4 = original.replace('+', '**');
            replacement5 = original.replace('+', '%');
            break;
          case '-':
            replacement = original.replace('-', '+');
            replacement2 = original.replace('-', '*');
            replacement3 = original.replace('-', '/');
            replacement4 = original.replace('-', '**');
            replacement5 = original.replace('-', '%');
            break;
          case '*':
            replacement = original.replace('*', '+');
            replacement2 = original.replace('*', '-');
            replacement3 = original.replace('*', '/');
            replacement4 = original.replace('*', '**');
            replacement5 = original.replace('*', '%');
            break;
          case '**':
            replacement = original.replace('**', '+');
            replacement2 = original.replace('**', '-');
            replacement3 = original.replace('**', '*');
            replacement4 = original.replace('**', '/');
            replacement5 = original.replace('**', '%');
            break;
          case '/':
            replacement = original.replace('/', '+');
            replacement2 = original.replace('/', '-');
            replacement3 = original.replace('/', '*');
            replacement4 = original.replace('/', '**');
            replacement5 = original.replace('/', '%');
            break;
          case '%':
            replacement = original.replace('%', '+');
            replacement2 = original.replace('%', '-');
            replacement3 = original.replace('%', '*');
            replacement4 = original.replace('%', '/');
            replacement5 = original.replace('%', '**');
            break;
          // Bitwise operators
          case '<<':
            replacement = original.replace('<<', '>>');
            break;
          case '>>':
            replacement = original.replace('>>', '<<');
            break;
          case '|':
            replacement = original.replace('|', '&');
            replacement2 = original.replace('|', '^');
            break;
          case '&':
            replacement = original.replace('&', '|');
            replacement2 = original.replace('&', '^');
            break;
          case '^':
            replacement = original.replace('^', '&');
            replacement2 = original.replace('^', '|');
            break;
          // Logical operators
          case '&&':
            replacement = original.replace('&&', '||');
            break;
          case '||':
            replacement = original.replace('||', '&&');
            break;
          // Relational operators
          case '<':
            replacement = original.replace('<', '<=');
            replacement2 = original.replace('<', '>=');
            replacement3 = original.replace('<', '>');
            replacement4 = original.replace('<', '!=');
            replacement5 = original.replace('<', '==');
            break;
          case '>':
            replacement = original.replace('>', '>=');
            replacement2 = original.replace('>', '<=');
            replacement3 = original.replace('>', '<');
            replacement4 = original.replace('>', '!=');
            replacement5 = original.replace('>', '==');
            break;
          case '<=':
            replacement = original.replace('<=', '<');
            replacement2 = original.replace('<=', '>');
            replacement3 = original.replace('<=', '>=');
            replacement4 = original.replace('<=', '!=');
            replacement5 = original.replace('<=', '==');
            break;
          case '>=':
            replacement = original.replace('>=', '<');
            replacement2 = original.replace('>=', '>');
            replacement3 = original.replace('>=', '<=');
            replacement4 = original.replace('>=', '!=');
            replacement5 = original.replace('>=', '==');
            break;
          case '!=':
            replacement = original.replace('!=', '>');
            replacement2 = original.replace('!=', '<');
            replacement3 = original.replace('!=', '<=');
            replacement4 = original.replace('!=', '>=');
            replacement5 = original.replace('!=', '==');
            break;
          case '==':
            replacement = original.replace('==', '<=');
            replacement2 = original.replace('==', '>=');
            replacement3 = original.replace('==', '<');
            replacement4 = original.replace('==', '>');
            replacement5 = original.replace('==', '!=');
            break;
        }

        // Push the mutations to the list
        if (replacement) {
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
        }
        if (replacement2) {
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement2, this.ID));
        }
        if (replacement3) {
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement3, this.ID));
        }
        if (replacement4) {
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement4, this.ID));
        }
        if (replacement5) {
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement5, this.ID));
        }
      }
    }
  });

  return mutations;
}

module.exports = BOROperator;
