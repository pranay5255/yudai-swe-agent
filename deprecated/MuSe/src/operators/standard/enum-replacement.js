const Mutation = require('../../mutation');

/**
 * EROperator is a mutation testing operator designed to test changes in enums within Solidity smart contracts.
 * 
 * **Purpose**:
 * This operator generates mutations to test how modifications to enums impact the smart contract's behavior. It performs two types of mutations:
 * 1. **Enum Replacement - Default Value (ERd)**: Changes the default value of an enum with another existing value.
 * 2. **Enum Replacement - Member (ERm)**: Replaces occurrences of an enum member in expressions with other enum members.
 * 
 * **How It Works**:
 * 1. **Identifies Enum Definitions**: It traverses the abstract syntax tree (AST) to find enum definitions.
 * 2. **Generates Mutations**:
 *    - **ERd (Enum Replacement - Default Value)**:
 *      - If the enum has more than one member, it replaces the default member value with another existing value.
 *    - **ERm (Enum Replacement - Member)**:
 *      - Replaces occurrences of an enum member in expressions with other enum members.
 * 
 * **Mutation Details**:
 * - **Enum Replacement - Default Value**:
 *   - Swaps the default enum member with another member, creating mutations to test the impact on the contract.
 * - **Enum Replacement - Member**:
 *   - For each occurrence of an enum member, generates mutations by replacing it with other members of the enum.
 * 
 * This script helps in evaluating how changes to enum values or members affect the smart contract's functionality, ensuring robustness and correctness.
 */

function EROperator() {
  this.ID = "ER";
  this.name = "enum-replacement";
}

EROperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];
  var ranges = []; // Track visited node ranges

  visit({
    EnumDefinition: (node) => {
      var thisEnum = node;

      // ERd - Enum Replacement - Default Value
      if (node.members.length > 1) {
        var start = node.members[0].range[0];
        var end = node.members[1].range[1] + 1;
        var startLine = node.members[0].loc.start.line;
        var endLine = node.members[1].loc.end.line;
        var defaultValue = node.members[0].name;
        var secondValue = node.members[1].name;

        var original = source.slice(start, end);
        var replacement = original.replace(defaultValue, "*")
                                 .replace(secondValue, defaultValue)
                                 .replace("*", secondValue);
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
      }

      // ERm - Enum Replacement - Member
      visit({
        MemberAccess: (node) => {
          if (!ranges.includes(node.range)) {
            ranges.push(node.range);
            if (node.expression.name === thisEnum.name) {
              var start = node.range[0];
              var end = node.range[1] + 1;
              var startLine = node.loc.start.line;
              var endLine = node.loc.end.line;
              var original = source.slice(start, end);

              // Replace a member with each existing member
              thisEnum.members.forEach(m => {
                if (m.name !== node.memberName) {
                  var replacement = original.replace(node.memberName, m.name);
                  mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
                }
              });
            }
          }
        }
      });
    }
  });

  return mutations;
}

module.exports = EROperator;
