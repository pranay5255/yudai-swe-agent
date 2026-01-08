const Mutation = require('../../mutation');

/**
 * EHCOperator is a mutation testing operator aimed at modifying exception handling statements in Solidity smart contracts.
 * 
 * **Purpose**:
 * This operator creates mutations by either commenting out or replacing exception handling statements. It helps to analyze how different modifications to exception handling impact the behavior and reliability of smart contracts.
 * 
 * **How It Works**:
 * 1. **Identifies Exception Handling Statements**: The operator searches for function calls to `require`, `assert`, and `revert`.
 * 2. **Generates Mutations**:
 *    - **Comment Out Statements**: Replaces each found exception handling statement with a commented-out version.
 *    - **Replace Statements** (Commented Out): It was planned to replace `require` with `assert` and vice versa, but this part is currently commented out.
 * 
 * **Mutation Details**:
 * - **Exception Handling Statement Deletion**:
 *   - Comments out the exception handling statement to effectively disable it.
 * 
 * - **Exception Handling Statement Replacement** (Commented Out):
 *   - Intended to replace `require` with `assert` and `assert` with `require`. This part is commented out but was planned to be part of the mutation strategy.
 * 
 * This script helps in evaluating how the absence or modification of exception handling affects the contract's functionality and error management.
 */

function EHCOperator() {
  this.ID = "EHC";
  this.name = "exception-handling-statement-change";
}

EHCOperator.prototype.getMutations = function (file, source, visit) {
  const mutations = [];
  const functions = ["require", "assert", "revert"];

  visit({
    FunctionCall: (node) => {
      if (functions.includes(node.expression.name)) {

        // EHD - Exception Handling Statement Deletion
        const start = node.range[0];
        var temp = source.slice(start);
        var delimiter = temp.indexOf(";");
        var end = start + delimiter + 1;
        const startLine = node.loc.start.line;
        const endLine = node.loc.end.line;
        const original = source.slice(start, end);
        var replacement = "/* " + original + " */";
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));

        // EHR - Exception Handling Statement Replacement
        /*
        end = node.range[1] + 1;

        if (node.expression.name == "require") {
          const condition = source.slice(node.arguments[0].range[0], node.arguments[0].range[1] + 1);
          replacement = "assert(" + condition + ")";
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
        }
        if (node.expression.name == "assert") {
          const condition = source.slice(node.arguments[0].range[0], node.arguments[0].range[1] + 1);
          replacement = "require(" + condition + ")";
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
        }
        */
      }
    }
  });
  return mutations;
};

module.exports = EHCOperator;
