const Mutation = require('../../mutation');

/**
 * UORDOperator is a mutation testing operator designed to replace unary operators in the code.
 * 
 * **Purpose**:
 * The operator focuses on replacing unary operators with their counterparts or removing them to test how such changes affect the behavior of the contract. This helps identify potential issues or vulnerabilities related to unary operations.
 * 
 * **How It Works**:
 * 1. **Identify Unary Operations**: The script searches for occurrences of unary operations in the code.
 * 2. **Perform Replacements**:
 *    - **Increment (`++`)**: Replaced with decrement (`--`) and with a space.
 *    - **Decrement (`--`)**: Replaced with increment (`++`) and with a space.
 *    - **Unary Minus (`-`)**: Replaced with a space.
 *    - **Bitwise NOT (`~`)**: Replaced with a space.
 *    - **Logical NOT (`!`)**: Replaced with a space.
 * 3. **Create Mutation Instances**: It creates and records mutations reflecting these replacements.
 * 4. **Return Mutations**: The list of mutations is returned for testing and further analysis.
 */

function UORDOperator() {
  this.ID = "UORD";
  this.name = "unary-operator-replacement";
}

UORDOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];
  var ranges = []; // Keeps track of visited node ranges

  visit({
    UnaryOperation: (node) => {
      if (!ranges.includes(node.range)) {
        ranges.push(node.range);
        let replacement;
        let replacement2;

        var start;
        var end;

        if (node.isPrefix) {
          start = node.range[0];
          end = node.range[1];
        } else {
          start = node.range[0] + 1;
          end = node.range[1] + 1;
        }

        const startLine = node.loc.end.line;
        const endLine = node.loc.start.line;
        const original = source.slice(start, end);

        switch (node.operator) {
          // Unary Operator Replacement (Arithmetic)
          case "++":
            replacement = original.replace("++", "--");
            replacement2 = original.replace("++", " ");
            break;
          case "--":
            replacement = original.replace("--", "++");
            replacement2 = original.replace("--", " ");
            break;
          case "-":
            replacement = original.replace("-", " ");
            break;
          case "~":
            replacement = original.replace("~", " ");
            break;
          // Unary Operator Replacement (Conditional)
          case "!":
            replacement = original.replace("!", " ");
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

module.exports = UORDOperator;
