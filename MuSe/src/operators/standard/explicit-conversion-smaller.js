const Mutation = require('../../mutation');

/**
 * ECSOperator is a mutation testing operator designed to mutate explicit type conversions to smaller types in Solidity smart contracts.
 * 
 * **Purpose**:
 * This operator tests the impact of changing data types to their smaller counterparts. It aims to evaluate how reducing the size of types affects the contract's behavior and performance.
 * 
 * **How It Works**:
 * 1. **Identifies Type Conversions**: Searches for function calls where the type being converted is an elementary type (`uint`, `int`, `bytes`).
 * 2. **Generates Mutations**:
 *    - **Convert to Smaller Types**: Replaces the type in the function call with a smaller type (`uint8` instead of `uint256`, `int8` instead of `int256`, `bytes1` instead of `bytes32`, etc.).
 * 
 * **Mutation Details**:
 * - **uint Types**: Converts `uint` types to `uint8` if they are not already `uint8`.
 * - **int Types**: Converts `int` types to `int8` if they are not already `int8`.
 * - **bytes Types**: Converts `bytes` types to `bytes1` if they are not already `bytes1`.
 * 
 * This script helps in evaluating the impact of reducing data type sizes on smart contract operations, potentially uncovering issues related to overflow, underflow, or incorrect data handling.
 */

function ECSOperator() {
  this.ID = "ECS";
  this.name = "explicit-conversion-to-smaller-type";
}

ECSOperator.prototype.getMutations = function (file, source, visit) {
  const mutations = [];
  var replacement, original, start, end, startLine, endLine;

  visit({
    FunctionCall: (node) => {
      if (node.expression.type === "ElementaryTypeName") {
        var type = node.expression.name;
        start = node.range[0];
        end = node.range[1] + 1;
        startLine = node.loc.start.line;
        endLine = node.loc.end.line;
        original = source.slice(start, end);

        if (type.startsWith("uint") && type !== "uint8") {
          replacement = original.replace(type, "uint8");
          pushMutation(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
        }
        else if (type.startsWith("int") && type !== "int8") {
          replacement = original.replace(type, "int8");
          pushMutation(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
        }
        else if (type.startsWith("bytes") && type !== "bytes1") {
          replacement = original.replace(type, "bytes1");
          pushMutation(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
        }
      }
    }
  });

  // Apply mutations
  function pushMutation(mutation) {
    // Ensure that the mutation is unique before adding it to the list
    if (!mutations.find(m => m.id === mutation.id)) {
      mutations.push(mutation);
    }
  }

  return mutations;
};

module.exports = ECSOperator;
