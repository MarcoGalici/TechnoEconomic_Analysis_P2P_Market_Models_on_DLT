// "SPDX-License-Identifier: UNLICENSED"

pragma solidity >=0.4.23;

import "./safemath.sol";

contract erc20{

    using safemath for uint256;

    // uint256 totalSupply_;
    string private _name;
    string private _symbol;

    constructor(string memory name_, string memory symbol_) {
        _name = name_;
        _symbol = symbol_;
    }

    event Transfer(address, address, uint);
    event Set(address, uint);

    mapping(address => uint256) public balances;

    /**
     * @dev Returns the name of the token.
     */
    function name() public view returns (string memory) {
        return _name;
    }

    /**
     * @dev Returns the symbol of the token, usually a shorter version of the
     * name.
     */
    function symbol() public view returns (string memory) {
        return _symbol;
    }

    function setBalance(uint _totalSupply) public returns (bool) {
        balances[msg.sender] = _totalSupply;
        emit Set(msg.sender, _totalSupply);
        return true;
    }

    function balanceOf(address tokenOwner) public view returns (uint) {
        return balances[tokenOwner];
    }

    function transfer(address sender, address receiver, uint numTokens) public returns (bool) {
        require(numTokens <= balances[sender]);
        balances[sender] = balances[sender].sub(numTokens);
        balances[receiver] = balances[receiver].add(numTokens);
        emit Transfer(sender, receiver, numTokens);
        return true;
    }

}
