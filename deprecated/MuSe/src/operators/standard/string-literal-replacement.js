const Mutation = require('../../mutation');

/**
 * SLRoperator is a mutation testing operator designed to replace string literals within Solidity smart contracts.
 * 
 * **Purpose**:
 * The operator aims to test how the contract behaves when string literals are replaced with empty strings. String literals in contracts are often used for logging, error messages, or other textual outputs. By replacing these literals with empty strings, the mutation helps to evaluate how the contract handles missing or altered textual data.
 * 
 * **How It Works**:
 * 1. **Identify Exception Handling Functions**: The script first identifies function calls for exception handling functions (`require`, `assert`, `revert`) and ignores any string literals used within these calls to avoid altering critical error messages.
 * 2. **Identify Import Statements**: It identifies import statements to avoid replacing string literals used in import paths.
 * 3. **Replace String Literals**: For each string literal found in the contract, if it is not part of exception handling or import statements, it is replaced with an empty string.
 * 4. **Create Mutation Instances**: These mutations are then added to a list for further analysis and testing.
 */

function SLRoperator() {
  this.ID = "SLR";
  this.name = "string-literal-replacement";
}

SLRoperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];
  let prevRange;
  const importStatements = [];
  const excHandFunctions = ["require", "assert", "revert"];
  const ignoreIndexes = [];

  // Retrieve indexes of exception handling functions to ignore
  visit({
    FunctionCall: (node) => {
      if (excHandFunctions.includes(node.expression.name)) {
        let ignore = {};
        const start = node.range[0];
        ignore.start = start;
        const temp = source.slice(start);
        const delimiter = temp.indexOf(";");
        ignore.end = start + delimiter + 1;
        ignoreIndexes.push(ignore);
      }
    }
  });

  // Retrieve import statements to ignore
  visit({
    ImportDirective: (node) => {
      importStatements.push(node.path);
    }
  });

  // Replace string literals with empty strings, except those in ignored ranges
  visit({
    StringLiteral: (node) => {
      if (prevRange !== node.range) {
        if (node.value) {
          const start = node.range[0];
          const end = node.range[1] + 1;
          const startLine = node.loc.start.line;
          const endLine = node.loc.end.line;
          const original = source.slice(start, end);
          let mutate = true;

          // Check if the string literal is part of an ignored section or an import statement
          if (!importStatements.includes(original.replaceAll("\"", ""))) {
            for (let i = 0; i < ignoreIndexes.length; i++) {
              const e = ignoreIndexes[i];
              if (start >= e.start && end <= e.end) {
                mutate = false;
                break;
              }
            }
            if (mutate) {
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, "\"\"", this.ID));
            }
          }
        }
      }
      prevRange = node.range;
    }
  });

  return mutations;
};

module.exports = SLRoperator;
