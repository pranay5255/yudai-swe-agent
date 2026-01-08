const Mutation = require('../../mutation');

/**
 * FVROperator is a mutation testing operator designed to mutate the visibility of functions in Solidity smart contracts.
 * 
 * **Purpose**:
 * This operator tests the impact of changing the visibility of function definitions. It aims to evaluate how different visibility levels affect the contract's security, functionality, and accessibility.
 * 
 * **How It Works**:
 * 1. **Identifies Function Definitions**: Searches for function definitions in the Solidity contract that are not receive Ether functions, fallback functions, virtual functions, or functions with an override.
 * 2. **Generates Mutations**:
 *    - **Constructor Visibility**: For constructors, it switches between `public` and `internal`.
 *    - **Standard Function Visibility**: For standard functions, it cycles through `public`, `external`, `internal`, and `private` based on the current visibility.
 * 
 * **Mutation Details**:
 * - **Constructors**: 
 *   - `public` ↔ `internal`
 * - **Standard Functions**:
 *   - `public` ↔ `external` (additional replacements to `internal` and `private` if not payable)
 *   - `external` ↔ `public` (additional replacements to `internal` and `private` if not payable)
 *   - `internal` ↔ `public`, `external`, `private`
 *   - `private` ↔ `public`, `external`, `internal`
 * 
 * This script helps in evaluating how changes in function visibility affect the contract's behavior, security, and accessibility.
 */

function FVROperator() {
  this.ID = "FVR";
  this.name = "function-visibility-replacement";
}

FVROperator.prototype.getMutations = function (file, source, visit) {
  const mutations = [];

  visit({
    FunctionDefinition: (node) => {
      if (!node.isReceiveEther && !node.isFallback && !node.isVirtual && node.override == null) {
        if (node.body) {
          const start = node.range[0];
          const end = node.body.range[0];
          const startLine = node.loc.start.line;
          const endLine = node.body.loc.start.line;
          const original = source.substring(start, end); // function signature
          let replacement;
          let replacement2;
          let replacement3;

          // Constructor
          if (node.isConstructor) {
            if (node.visibility === "public") {
              replacement = original.replace("public", "internal");
            } else if (node.visibility === "internal") {
              replacement = original.replace("internal", "public");
            }
          }
          // Standard function
          else {
            switch (node.visibility) {
              case "public":
                replacement = original.replace("public", "external");
                if (node.stateMutability !== "payable") {
                  replacement2 = original.replace("public", "internal");
                  replacement3 = original.replace("public", "private");
                }
                break;
              case "external":
                replacement = original.replace("external", "public");
                if (node.stateMutability !== "payable") {
                  replacement2 = original.replace("external", "internal");
                  replacement3 = original.replace("external", "private");
                }
                break;
              case "internal":
                replacement = original.replace("internal", "public");
                replacement2 = original.replace("internal", "external");
                replacement3 = original.replace("internal", "private");
                break;
              case "private":
                replacement = original.replace("private", "public");
                replacement2 = original.replace("private", "external");
                replacement3 = original.replace("private", "internal");
                break;
            }
          }

          if (replacement)
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
          if (replacement2)
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement2, this.ID));
          if (replacement3)
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement3, this.ID));
        }
      }
    }
  });
  return mutations;
};

module.exports = FVROperator;
