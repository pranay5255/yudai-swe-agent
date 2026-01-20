const Mutation = require("../../mutation");

/**
 * The VVRoperator class performs mutation testing by replacing visibility modifiers of state variables.
 * Visibility modifiers determine the accessibility of state variables in smart contracts. This script helps to test how 
 * changing these visibility modifiers affects the behavior and security of the contract.
 * 
 * The script handles the following visibility modifiers:
 * - `public` is replaced with `internal`
 * - `internal` is replaced with `public`
 * - `private` is replaced with `public`
 * - If no visibility is specified, it defaults to `public`
 */

function VVRoperator() {
  this.ID = "VVR";
  this.name = "variable-visibility-replacement";
}

/**
 * Generates mutations by replacing the visibility modifiers of state variables.
 * 
 * @param {string} file - The name of the file being mutated.
 * @param {string} source - The source code of the file.
 * @param {function} visit - A function to visit nodes in the source code's abstract syntax tree (AST).
 * @returns {Array} - An array of Mutation objects representing the generated mutations.
 */
VVRoperator.prototype.getMutations = function (file, source, visit) {
  const mutations = [];

  // Visit each StateVariableDeclaration node in the source code
  visit({
    StateVariableDeclaration: (node) => {
      // Skip variables of type Mapping
      if (node.variables[0].typeName.type != "Mapping") {

        const start = node.range[0];
        const end = node.range[1];
        const startLine = node.loc.start.line;
        const endLine = node.loc.end.line;
        const original = source.slice(start, end);
        let replacement;
        var varDeclaration = source.substring(node.range[0], node.range[1]);

        // Determine replacement visibility based on current visibility
        switch (node.variables[0].visibility) {
          case "public":
            replacement = varDeclaration.replace("public", "internal");
            break;
          case "internal":
            replacement = varDeclaration.replace("internal", "public");
            break;
          case "private":
            replacement = varDeclaration.replace("private", "public");
            break;
          case "default": // No visibility specified
            var varName = node.variables[0].name.toString();
            var varType;
            if (node.variables[0].typeName.name) {  // Typename
              varType = node.variables[0].typeName.name.toString();
            } else if (node.variables[0].typeName.namePath) { // User defined typename
              varType = node.variables[0].typeName.namePath.toString();
            }
            // Replace default visibility with public
            var slice1 = varDeclaration.split(varName)[0];
            var slice2 = varDeclaration.split(varType)[1];
            replacement = slice1 + "public" + slice2;
            break;
        }

        // Create a Mutation object if a replacement is made
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
      }
    }
  });

  return mutations;
};

module.exports = VVRoperator;
