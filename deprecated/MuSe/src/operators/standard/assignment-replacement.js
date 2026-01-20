const Mutation = require('../../mutation');

/**
 * AOROperator is a mutation testing operator for replacing assignment operators.
 * This script identifies occurrences of assignment operators (like `+=`, `-=`, etc.) in the code and generates mutations by replacing these operators with other possible operators. The purpose is to test whether existing tests can catch errors introduced by these mutations.
 * For example, if the original code has an operator `+=`, the script will create mutations where `+=` is replaced with `-=` (subtraction assignment), `*=` (multiplication assignment), `/=` (division assignment), and `%=` (modulus assignment), among others. This helps in assessing the code's robustness against such changes.
 */

function AOROperator() {
  this.ID = "AOR";
  this.name = "assignment-operator-replacement";
}

AOROperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  // Visit each BinaryOperation node
  visit({
    BinaryOperation: (node) => {
      // Calculate start and end positions of the mutation range
      const start = node.left.range[1] + 1;
      const end = node.right.range[0];
      const startLine = node.left.loc.end.line;
      const endLine = node.right.loc.start.line;
      const original = source.slice(start, end);
      
      let replacement, replacement2, replacement3, replacement4, replacement5;

      // Determine replacements based on the operator
      switch (node.operator) {
        case '+=':
          replacement = original.replace('+=', '-=');
          replacement2 = original.replace('+=', ' =');
          replacement3 = original.replace('+=', '/=');
          replacement4 = original.replace('+=', '*=');
          replacement5 = original.replace('+=', '%=');
          break;
        case '-=':
          replacement = original.replace('-=', '+=');
          replacement2 = original.replace('-=', ' =');
          replacement3 = original.replace('-=', '/=');
          replacement4 = original.replace('-=', '*=');
          replacement5 = original.replace('-=', '%=');
          break;
        case '*=':
          replacement = original.replace('*=', '/=');
          replacement2 = original.replace('*=', ' =');
          replacement3 = original.replace('*=', '+=');
          replacement4 = original.replace('*=', '-=');
          replacement5 = original.replace('*=', '%=');
          break;
        case '/=':
          replacement = original.replace('/=', '*=');
          replacement2 = original.replace('/=', ' =');
          replacement3 = original.replace('/=', '+=');
          replacement4 = original.replace('/=', '-=');
          replacement5 = original.replace('/=', '%=');
          break;
        case '%=':
          replacement = original.replace('%=', '*=');
          replacement2 = original.replace('%=', ' =');
          replacement3 = original.replace('%=', '+=');
          replacement4 = original.replace('%=', '-=');
          replacement5 = original.replace('%=', '/=');
          break;
        case '<<=':
          replacement = original.replace('<<=', '>>=');
          replacement2 = original.replace('<<=', ' =');
          break;
        case '>>=':
          replacement = original.replace('>>=', '<<=');
          replacement2 = original.replace('>>=', ' =');
          break;
        case '|=':
          replacement = original.replace('|=', '&=');
          replacement2 = original.replace('|=', ' =');
          replacement3 = original.replace('|=', '^=');
          break;
        case '&=':
          replacement = original.replace('&=', '|=');
          replacement2 = original.replace('&=', ' =');
          replacement3 = original.replace('&=', '^=');
          break;
        case '^=':
          replacement = original.replace('^=', '&=');
          replacement2 = original.replace('^=', ' =');
          replacement3 = original.replace('^=', '|=');
          break;
      }

      // Add mutations to the list if replacements exist
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
    },
  });

  return mutations;
}

module.exports = AOROperator;
