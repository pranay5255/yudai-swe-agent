const Mutation = require('../../mutation');

/**
 * VVRoperator is a mutation testing operator for changing the visibility of state variables in Solidity contracts.
 * 
 * **Purpose**:
 * The operator modifies the visibility of state variables to test the robustness of smart contracts against such changes. It ensures that the contract behaves correctly even when variable access levels are altered.
 * 
 * **How It Works**:
 * 1. **Identify State Variable Declarations**: The script searches for state variable declarations.
 * 2. **Perform Replacements**:
 *    - **Change Visibility**: Replaces `public`, `internal`, and `private` visibility specifiers with each other. For variables without explicit visibility, it adds `public` or `private`.
 * 3. **Create Mutation Instances**: Records mutations reflecting these visibility changes.
 * 4. **Return Mutations**: The list of mutations is returned for testing and further analysis.
 */

function VVRoperator() {
  this.ID = "VVR";
  this.name = "variable-visibility-replacement";
}

VVRoperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  visit({
    StateVariableDeclaration: (node) => {
      // Skip mappings, as their visibility is not considered in this mutation
      if (node.variables[0].typeName.type !== "Mapping") {

        const start = node.range[0];
        const end = node.range[1];
        const startLine = node.loc.start.line;
        const endLine = node.loc.end.line;
        const original = source.slice(start, end);
        let replacement, replacement2;
                
        // Extract the variable declaration string from the source
        var varDeclaration = source.substring(node.range[0], node.range[1]);

        switch (node.variables[0].visibility) {
          case "public":
            // Replace public visibility with internal and private
            replacement = varDeclaration.replace("public", "internal");
            replacement2 = varDeclaration.replace("public", "private");
            break;
          case "internal":
            // Replace internal visibility with public and private
            replacement = varDeclaration.replace("internal", "public");
            replacement2 = varDeclaration.replace("internal", "private");
            break;
          case "private":
            // Replace private visibility with public and internal
            replacement = varDeclaration.replace("private", "public");
            replacement2 = varDeclaration.replace("private", "internal");
            break;
          case "default":
            // No visibility specified, add public and private
            var varName = node.variables[0].name.toString();
            var varType;

            if (node.variables[0].typeName.name) {  
              varType = node.variables[0].typeName.name.toString();
            } else if (node.variables[0].typeName.namePath) { 
              varType = node.variables[0].typeName.namePath.toString();
            }

            // Construct replacements for default visibility
            var slice1 = varDeclaration.split(varName)[0];
            var slice2 = varDeclaration.split(varType)[1];
            replacement = slice1 + "public" + slice2;
            replacement2 = slice1 + "private" + slice2;
            break;
        }

        // Create mutations for each replacement
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement2, this.ID));
      }
    }
  });

  return mutations;
};

module.exports = VVRoperator;
