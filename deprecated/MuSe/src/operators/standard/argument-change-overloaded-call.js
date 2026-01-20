const Mutation = require("../../mutation");

/**
 * The ACMOperator class performs mutation testing by modifying arguments of overloaded method calls.
 * Overloaded methods are functions with the same name but different parameter lists. This script aims to:
 * 1. Identify overloaded functions within the source code.
 * 2. Collect function calls to these overloaded functions.
 * 3. Apply mutations by swapping arguments between function calls with the same function name but different parameter lists.
 * 
 * This helps test how the code handles variations in function arguments and ensures robustness against such changes.
 */

function ACMOperator() {
  this.ID = "ACM";
  this.name = "argument-change-of-overloaded-method-call";
}

ACMOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];
  var functions = [];
  var overloadedFunctions = [];
  var calls = [];
  var ranges = []; // Track visited node ranges

  // Collect function definitions and identify overloaded functions
  visitFunctionDefinition(mutate);

  /**
   * Visits function definitions to collect function names and identify overloaded functions.
   * @param {Function} callback - Function to execute after visiting function definitions.
   */
  function visitFunctionDefinition(callback) {
    // Save defined function names
    visit({
      FunctionDefinition: (node) => {
        if (!ranges.includes(node.range)) {
          ranges.push(node.range);
          if (node.name) {
            functions.push(node.name);
          }
        }
      }
    });

    // Determine overloaded functions by counting occurrences of function names
    const lookup = functions.reduce((a, e) => {
      a[e] = ++a[e] || 0;
      return a;
    }, {});
    overloadedFunctions = functions.filter(e => lookup[e] > 1);

    // Proceed if there are overloaded functions
    if (overloadedFunctions.length > 0) {
      callback();
    }
  }

  /**
   * Visits function calls and identifies calls to overloaded functions.
   */
  function mutate() {
    // Collect function calls to overloaded functions
    visit({
      FunctionCall: (node) => {
        if (overloadedFunctions.includes(node.expression.name)) {
          calls.push(node);
        }
      }
    });

    // Apply mutations if there are overloaded function calls
    if (calls.length > 0) {
      calls.forEach(f => {
        for (var i = 0; i < calls.length; i++) {
          var r = calls[i];

          // If calls have the same function name but different number of arguments
          if (f !== r && f.expression.name === r.expression.name) {
            if (f.arguments.length !== r.arguments.length) {
              apply(f, r);
              break;
            }
            // If calls have the same number of arguments but different argument types
            else {
              for (var j = 0; j < f.arguments.length; j++) {
                if (f.arguments[j].type !== r.arguments[j].type) {
                  apply(f, r);
                  break;
                }
              }
              break;
            }
          }
        }
      });
    }
  }

  /**
   * Applies a mutation by replacing the arguments of one function call with those of another.
   * @param {Object} originalNode - The original function call node.
   * @param {Object} replacementNode - The replacement function call node.
   */
  function apply(originalNode, replacementNode) {
    let oStart = originalNode.range[0];
    let oEnd = originalNode.range[1] + 1;
    let oLineStart = originalNode.loc.start.line;
    let oLineEnd = originalNode.loc.end.line;
    let rStart = replacementNode.range[0];
    let rEnd = replacementNode.range[1] + 1;

    var original = source.slice(oStart, oEnd);
    var replacement = source.slice(rStart, rEnd);

    // Record the mutation
    mutations.push(new Mutation(file, oStart, oEnd, oLineStart, oLineEnd, original, replacement, this.ID));
  }

  return mutations;
};

module.exports = ACMOperator;
