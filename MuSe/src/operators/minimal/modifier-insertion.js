const Mutation = require("../../mutation");

/**
 * The MOIOperator class is designed to insert modifiers into functions that do not currently have any.
 * This mutation operator helps in evaluating whether the code and its existing tests can handle additional modifiers.
 * The script first collects all available modifiers and then applies them to functions that do not have any modifiers.
 * The mutations are then used to test if the function's behavior changes appropriately with the added modifiers.
 */

function MOIOperator() {
  this.ID = "MOI";
  this.name = "modifier-insertion";
}

/**
 * Generates mutations for inserting modifiers into functions that do not have any.
 * 
 * @param {string} file - The name of the file being mutated.
 * @param {string} source - The source code of the file.
 * @param {function} visit - A function to visit nodes in the source code's abstract syntax tree (AST).
 * @returns {Array} - An array of Mutation objects representing the generated mutations.
 */
MOIOperator.prototype.getMutations = function (file, source, visit) {
  const ID = this.ID;
  const mutations = [];
  var modifiers = []; // List of modifiers found in the code
  var modifiersNodes = []; // Modifier nodes corresponding to the modifiers

  // Start the process of collecting modifier nodes and their corresponding strings
  visitModifiers(visitFunctions);

  /**
   * Collects all modifier nodes and their corresponding source code strings.
   * Once collected, it reverses the order to reduce the likelihood of selecting invalid modifiers.
   * Then, it proceeds to visit functions to apply the modifiers.
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
   * Visits function definitions and applies available modifiers to functions that do not have any.
   */
  function visitFunctions() {
    visit({
      FunctionDefinition: (fNode) => {
        // Proceed only if the function has no modifiers and is not special (constructor, fallback, receive, pure, or view)
        if (fNode.modifiers.length === 0 && fNode.body &&
            !fNode.isConstructor && !fNode.isReceiveEther && !fNode.isFallback &&
            (!fNode.stateMutability || (fNode.stateMutability !== "pure" && fNode.stateMutability !== "view"))) {

          // Iterate through the available modifier nodes
          for (let i = 0; i < modifiersNodes.length; i++) {
            const mNode = modifiersNodes[i];

            // If the modifier has parameters, they must match the function's parameters
            if (mNode.arguments) {
              if (fNode.parameters) {
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
    });
  }

  /**
   * Applies a mutation by inserting the modifier into the function's signature.
   * 
   * @param {object} functionNode - The function node to be mutated.
   * @param {object} modifierNode - The modifier node to be inserted.
   * @returns {Mutation} - A Mutation object representing the applied mutation.
   */
  function mutate(functionNode, modifierNode) {
    if (contractContaining(functionNode) === contractContaining(modifierNode) &&
        contractContaining(functionNode)) {

      var startF = functionNode.range[0];
      var endF = functionNode.body.range[0];
      var original = source.substring(startF, endF); // Function signature
      const startLine = functionNode.loc.start.line;
      const endLine = functionNode.body.loc.start.line;

      var startM = modifierNode.range[0];
      var endM = modifierNode.range[1] + 1;
      var modifier = source.substring(startM, endM);

      // If the function has return parameters
      if (functionNode.returnParameters && functionNode.returnParameters.length > 0) {
        var slice1 = original.split("returns")[0];
        var slice2 = " returns" + original.split("returns")[1];
        var replacement = slice1 + modifier + slice2;
        return new Mutation(file, startF, endF, startLine, endLine, original, replacement, ID);
      }
      // If the function has no return parameters
      else {
        var replacement = original + modifier + " ";
        return new Mutation(file, startF, endF, startLine, endLine, original, replacement, ID);
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

module.exports = MOIOperator;
