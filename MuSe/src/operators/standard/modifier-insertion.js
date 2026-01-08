const Mutation = require('../../mutation');

/**
 * MOIOperator is a mutation testing operator designed to insert modifiers into function definitions in Solidity smart contracts.
 * 
 * **Purpose**:
 * This operator tests the impact of inserting existing modifiers into functions that currently do not have any, which can help identify potential security and logical flaws.
 * 
 * **How It Works**:
 * 1. **Identify Existing Modifiers**: Searches for all modifiers used in the contract.
 * 2. **Visit Non-Decorated Functions**:
 *    - For each function that does not have any modifiers, attempt to insert each identified modifier.
 * 
 * **Mutation Details**:
 * - For each identified function that has no modifiers, create mutations by inserting each identified modifier, provided the modifier parameters are compatible with the function parameters.
 */

function MOIOperator() {
  this.ID = "MOI";
  this.name = "modifier-insertion";
}

MOIOperator.prototype.getMutations = function (file, source, visit) {
  const ID = this.ID;
  const mutations = [];
  const modifiers = []; // Modifiers attached to functions
  const modifiersNodes = []; // Modifiers nodes attached to functions

  visitModifiers(visitFunctions);

  /**
   * Save attached modifiers and then call the provided callback.
   * @param {Function} callback - The callback function to be called after visiting modifiers.
   */
  function visitModifiers(callback) {
    visit({
      ModifierInvocation: (node) => {
        const m = source.slice(node.range[0], node.range[1] + 1);
        if (!modifiers.includes(m)) {
          modifiers.push(m);
          if (!modifiersNodes.includes(node)) {
            modifiersNodes.push(node);
          }
        }
      }
    });
    if (modifiers.length > 0) {
      callback();
    }
  }

  /**
   * Visit functions that are not decorated with any modifiers.
   */
  function visitFunctions() {
    visit({
      FunctionDefinition: (fNode) => {
        // If the function is not decorated with any modifiers
        if (fNode.modifiers.length === 0 && fNode.body) {
          // If the function is not a special function (constructor, fallback, or receive)
          if (!fNode.isConstructor && !fNode.isReceiveEther && !fNode.isFallback
            && (!fNode.stateMutability || (fNode.stateMutability !== "pure" && fNode.stateMutability !== "view"))) {

            // Iterate over the available modifiers nodes
            for (let i = 0; i < modifiersNodes.length; i++) {
              const mNode = modifiersNodes[i];

              // If the modifier has parameters, ensure they are compatible with the function parameters
              if (mNode.arguments) {

                // If the function has parameters
                if (fNode.parameters) {

                  const modArguments = mNode.arguments.map(e => e.name);
                  const funcArguments = fNode.parameters.map(e => e.name);

                  // If the parameters of the modifier are included in the parameters of the function
                  const params_included = modArguments.every((element, index) => element === funcArguments[index]);
                  if (params_included) {
                    const result = mutate(fNode, mNode);
                    if (result) {
                      mutations.push(result);
                    }
                  }
                } else {
                  // If the function does not have arguments, skip the mutation
                  break;
                }
              } else {
                // If the modifier does not have arguments
                const result = mutate(fNode, mNode);
                if (result) {
                  mutations.push(result);
                }
              }
            }
          }
        }
      }
    });
  }

  /**
   * Applies a mutation to the function by inserting a modifier.
   * @param {Object} functionNode - The function node to be mutated.
   * @param {Object} modifierNode - The modifier node to be inserted.
   * @returns {Object|boolean} - The mutation object or false if the mutation is not applicable.
   */
  function mutate(functionNode, modifierNode) {
    if (contractContaining(functionNode) === contractContaining(modifierNode) && contractContaining(functionNode)) {

      const startF = functionNode.range[0];
      const endF = functionNode.body.range[0];
      const original = source.substring(startF, endF); // Function signature
      const startLine = functionNode.loc.start.line;
      const endLine = functionNode.body.loc.start.line;

      const startM = modifierNode.range[0];
      const endM = modifierNode.range[1] + 1;
      const modifier = source.substring(startM, endM);

      let replacement;
      // If the function has return parameters
      if (functionNode.returnParameters && functionNode.returnParameters.length > 0) {
        const slice1 = original.split("returns")[0];
        const slice2 = " returns" + original.split("returns")[1];
        replacement = slice1 + modifier + slice2;
      } else {
        // If the function has no return parameters
        replacement = original + modifier + " ";
      }
      return new Mutation(file, startF, endF, startLine, endLine, original, replacement, ID);
    } else {
      return false;
    }
  }

  /**
   * Checks to which contract a node belongs.
   * @param {Object} node - The input node.
   * @returns {string|boolean} - The contract name or false if no contract is found.
   */
  function contractContaining(node) {
    const nodeStart = node.range[0];
    const nodeEnd = node.range[1];
    let cName = false;
    visit({
      ContractDefinition: (cNode) => {
        if (nodeStart >= cNode.range[0] && nodeEnd <= cNode.range[1]) {
          cName = cNode.name;
        }
      }
    });
    return cName;
  }

  return mutations;
};

module.exports = MOIOperator;
