const Mutation = require("../../mutation");

/**
 * The FVROperator class implements a mutation operator that targets function visibility in the code.
 * The FVROperator specifically modifies the visibility of functions (like changing from public to internal) 
 * to generate new mutants and test how the changes affect the contract's behavior.
 */

function FVROperator() {
  this.ID = "FVR";
  this.name = "function-visibility-replacement";
}

/**
 * The getMutations method generates a list of mutations for the given source code.
 * It scans the code for function definitions and creates mutations by replacing function visibility
 * with other visibility levels.
 *
 * @param {string} file - The name of the file being mutated.
 * @param {string} source - The source code of the file.
 * @param {function} visit - A function to visit nodes in the source code's abstract syntax tree (AST).
 * @returns {Array} - An array of Mutation objects representing the generated mutations.
 */
FVROperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  visit({
    FunctionDefinition: (node) => {
      if (!node.isReceiveEther && !node.isFallback && !node.isVirtual && node.override == null) {
        if (node.body) {
          const start = node.range[0];
          const end = node.body.range[0];
          const startLine = node.loc.start.line;
          const endLine = node.body.loc.start.line;
          const original = source.substring(start, end); // Function signature  
          let replacement;

          // Handle constructor visibility replacement
          if (node.isConstructor) {
            if (node.visibility === "public") {
              replacement = original.replace("public", "internal");
            } else if (node.visibility === "internal") {
              replacement = original.replace("internal", "public");
            }
          }
          // Handle standard function visibility replacement
          else {
            switch (node.visibility) {
              case "public":
                if (node.stateMutability !== "payable") {
                  replacement = original.replace("public", "internal");
                }
                break;
              case "external":
                if (node.stateMutability !== "payable") {
                  replacement = original.replace("external", "internal");
                }
                break;
              case "internal":
                replacement = original.replace("internal", "public");
                break;
              case "private":
                replacement = original.replace("private", "public");
                break;
            }
          }

          if (replacement) {
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
          }
        }
      }
    }
  });

  return mutations;
};

module.exports = FVROperator;
