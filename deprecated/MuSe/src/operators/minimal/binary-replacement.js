const Mutation = require("../../mutation");

/**
 * The BOROperator class implements a mutation operator that targets binary operators in the code.
 * The BOROperator specifically replaces binary operators (like +, -, *, /, etc.) with other binary operators
 * to generate new mutants.
 */

function BOROperator() {
  this.ID = "BOR";
  this.name = "binary-operator-replacement";
}

/**
 * The getMutations method generates a list of mutations for the given source code.
 * It scans the code for binary operations and creates mutations by replacing the binary operators with alternative ones.
 *
 * @param {string} file - The name of the file being mutated.
 * @param {string} source - The source code of the file.
 * @param {function} visit - A function to visit nodes in the source code's abstract syntax tree (AST).
 * @returns {Array} - An array of Mutation objects representing the generated mutations.
 */
BOROperator.prototype.getMutations = function (file, source, visit) {
  const mutations = [];
  var ranges = []; //Visited node ranges

  visit({
    BinaryOperation: (node) => {
      if (!ranges.includes(node.range)) {
        ranges.push(node.range);
        const start = node.left.range[1] + 1;
        const end = node.right.range[0];
        const startLine = node.left.loc.end.line;
        const endLine = node.right.loc.start.line;
        const original = source.slice(start, end);
        let replacement, replacement2;

        switch (node.operator) {
          //BORa - Binary Operator Replacement (Arithmetic)
          case "+":
            replacement = original.replace("+", "-");
            break;
          case "-":
            replacement = original.replace("-", "+");
            break;
          case "*":
            replacement = original.replace("*", "/");
            replacement2 = original.replace("*", "**");
            break;
          case "**":
            replacement = original.replace("**", "*");
            break;
          case "/":
            replacement = original.replace("/", "*");
            break;
          case "%":
            replacement = original.replace("%", "*");
            break;
          case "<<":
            replacement = original.replace("<<", ">>");
            break;
          case ">>":
            replacement = original.replace(">>", "<<");
            break;
          case "|":
            replacement = original.replace("|", "&");
            break;
          case "&":
            replacement = original.replace("&", "|");
            break;
          case "^":
            replacement = original.replace("^", "&");
            break;
          //BORc - Binary Operator Replacement (Conditional)
          case "&&":
            replacement = original.replace("&&", "||");
            break;
          case "||":
            replacement = original.replace("||", "&&");
            break;
          //BORr - Binary Operator Replacement (Relational)
          case "<":
            replacement = original.replace("<", "<=");
            replacement2 = original.replace("<", ">=");
            break;
          case ">":
            replacement = original.replace(">", ">=");
            replacement2 = original.replace(">", "<=");
            break;
          case "<=":
            replacement = original.replace("<=", "<");
            replacement2 = original.replace("<=", ">");
            break;
          case ">=":
            replacement = original.replace(">=", ">");
            replacement2 = original.replace(">=", "<");
            break;
          case "!=":
            replacement = original.replace("!=", "==");
            break;
          case "==":
            replacement = original.replace("==", "!=");
            break;
        }

        if (replacement) {
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
        }
        if (replacement2) {
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement2, this.ID));
        }
      }
    }
  });

  return mutations;
};

module.exports = BOROperator;
