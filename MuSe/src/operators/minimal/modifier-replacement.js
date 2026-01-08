const Mutation = require("../../mutation");

/**
 * The MOROperator class is designed to replace the first modifier attached to a function with a different valid modifier.
 * This mutation operator helps to test how replacing a modifier affects the function's behavior.
 * The script first collects all modifier instances and then iterates through functions with existing modifiers to apply a different modifier.
 * The generated mutations are used to test if the function behaves correctly with the altered modifiers.
 */

function MOROperator() {
  this.ID = "MOR";
  this.name = "modifier-replacement";
}

/**
 * Generates mutations by replacing the first modifier of a function with different valid modifiers.
 * 
 * @param {string} file - The name of the file being mutated.
 * @param {string} source - The source code of the file.
 * @param {function} visit - A function to visit nodes in the source code's abstract syntax tree (AST).
 * @returns {Array} - An array of Mutation objects representing the generated mutations.
 */
MOROperator.prototype.getMutations = function (file, source, visit) {
  const mutations = [];
  var modifiers = []; // List of modifier strings found in the code
  var modifiersNodes = []; // Modifier nodes corresponding to the modifier strings

  // Start the process of collecting modifier nodes and their corresponding strings
  visitModifiers(visitFunctions);

  /**
   * Collects all modifier nodes and their corresponding source code strings.
   * Once collected, it reverses the order to reduce the likelihood of selecting invalid modifiers.
   * Then, it proceeds to visit functions to apply the different modifiers.
   * 
   * @param {function} callback - The function to call after modifiers have been collected.
   */
  function visitModifiers(callback) {
    visit({
      ModifierInvocation: (node) => {
        var m = source.slice(node.range[0], node.range[1] + 1);
        if (!modifiers.includes(m)) {
          modifiers.push(m);
          if (!modifiersNodes.includes(node)) {
            modifiersNodes.push(node);
          }
        }
      }
    });
    if (modifiers.length > 0) {
      // Reverse the arrays to minimize the chance of picking an invalid modifier
      modifiers = modifiers.reverse();
      modifiersNodes = modifiersNodes.reverse();
      callback();
    }
  }

  /**
   * Visits function definitions that have modifiers and attempts to replace the first modifier with a different one.
   */
  function visitFunctions() {
    visit({
      FunctionDefinition: (fNode) => {
        // Proceed only if the function has one or more modifiers
        if (fNode.modifiers.length > 0) {
          // Proceed only if the function is not special (constructor, fallback, or receive)
          if (fNode.body && !fNode.isConstructor && !fNode.isReceiveEther && !fNode.isFallback) {

            // Iterate through the available modifier nodes
            for (let i = 0; i < modifiersNodes.length; i++) {
              const mNode = modifiersNodes[i];

              // If the modifier has parameters, they must match the function's parameters
              if (mNode.arguments && mNode.arguments.length > 0) {

                // If the function has parameters
                if (fNode && fNode.parameters) {

                  var modArguments = [];
                  var funcArguments = [];

                  // Extract parameter names from modifier and function
                  mNode.arguments.forEach(e => {
                    if (e.name) modArguments.push(e.name);
                  });

                  fNode.parameters.forEach(e => {
                    funcArguments.push(e.name);
                  });

                  // Check if modifier parameters are included in function parameters
                  if (modArguments.length > 0) {
                    var params_included = modArguments.every(function (element, index) {
                      return element === funcArguments[index];
                    });
                    if (params_included) {
                      const result = mutate(fNode, mNode);
                      if (result) {
                        mutations.push(result);
                        break;
                      }
                    }
                  }
                } else {
                  break;
                }
              } else {
                const result = mutate(fNode, mNode);
                if (result) {
                  mutations.push(result);
                  break;
                }
              }
            }
          }
        }
      }
    });
  }

  /**
   * Checks if the modifier is a valid candidate for replacing the existing modifier.
   * The modifier must be from the same contract and must not already be attached to the function.
   * 
   * @param {object} functionNode - The function node to be mutated.
   * @param {object} modifierNode - The modifier node to be used as a replacement.
   * @returns {Mutation|boolean} - A Mutation object if the replacement is valid, otherwise false.
   */
  function mutate(functionNode, modifierNode) {
    if (contractContaining(functionNode) === contractContaining(modifierNode) &&
        contractContaining(functionNode)) {

      // Retrieve modifiers attached to the current function node
      var funcModifiers = [];
      functionNode.modifiers.forEach(m => {
        funcModifiers.push(source.slice(m.range[0], m.range[1] + 1));
      });

      // Prepare to replace the first modifier attached to the current function node
      var start = functionNode.modifiers[0].range[0];
      var end = functionNode.modifiers[0].range[1] + 1;
      const startLine = functionNode.loc.start.line;
      const endLine = functionNode.body.loc.start.line;
      var original = source.substring(start, end);  // Original modifier
      var replacement = source.slice(modifierNode.range[0], modifierNode.range[1] + 1); // Replacement modifier

      // Ensure the replacement is not the same as the original and is not already present in function modifiers
      if (replacement !== original && !funcModifiers.find(m => m === replacement)) {
        const mutation = new Mutation(file, start, end, startLine, endLine, original, replacement, ID);
        return mutation;
      } else {
        return false;
      }
    } else {
      return false;
    }
  }

  /**
   * Determines which contract a node belongs to.
   * 
   * @param {object} node - The node whose containing contract is to be determined.
   * @returns {string|boolean} - The contract name if the node belongs to a contract, otherwise false.
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

module.exports = MOROperator;
