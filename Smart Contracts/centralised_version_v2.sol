// "SPDX-License-Identifier: UNLICENSED"

pragma solidity >=0.4.23;

import "./safemath.sol";

contract DAmarket{

    using safemath for uint256;

    address public Master;
    uint public indexTime;
    uint public buyGrid;
    uint public sellGrid;

    constructor(address M){
        Master = M;
        indexTime = 0;
    }

    struct Participant{
        address add;
        uint balance;
    }

    struct Contract{
        address seller;
        address buyer;
        uint price;
        uint quantity;
    }

    struct Offer{
        address user;
        bool buyer_seller;  // true=buyer ; false=seller
        uint price;
        uint quantity;
        uint idxTime;
    }


    mapping(address => Participant) public meters;
    mapping(address => Offer) public adrsOffer;
    mapping(uint => Contract[]) public contracts;

    mapping(uint => Offer[]) public marketListB;
    mapping(uint => Offer[]) public marketListS;

    mapping(uint => Offer[]) public orderBook_B;
    mapping(uint => Offer[]) public orderBook_S;

    mapping(uint => uint[]) public priceS;
    mapping(uint => uint[]) public idxS;

    mapping(uint => uint[]) public priceB;
    mapping(uint => uint[]) public idxB;


    // ########### Master functions ##########################################################################################################
    function setPrices(uint _bGrid, uint _sGrid) public {
        require(msg.sender == Master);
        buyGrid = _bGrid;
        sellGrid = _sGrid;
    }


    // ########### Token functions ##########################################################################################################
    event Transfer(address, address, uint);


    function balanceOf(address tokenOwner) public view returns (uint) {
        return meters[tokenOwner].balance;
    }


    function transfer(address sender, address receiver, uint numTokens, uint amount) public returns (bool) {
        uint senderBalance = meters[sender].balance;
        uint receiverBalance = meters[receiver].balance;
        // Ricordarsi di registrare ogni partecipante (anche Master) altrimenti restituisce revert qui.
        require(numTokens <= senderBalance, "Not enough Token to proceed with the transaction");

        meters[sender].balance = senderBalance.sub(numTokens);
        meters[receiver].balance = receiverBalance.add(numTokens);

        contracts[indexTime].push(Contract({seller: receiver, buyer: sender, price: numTokens, quantity: amount}));

        emit Transfer(sender, receiver, numTokens);
        return true;
    }


    // ########### Participant functions ###################################################################################################
    function setIssuer() public {
        // create the participant
        Participant memory newParticipant = Participant({add: msg.sender, balance: 1000});
        meters[msg.sender] = newParticipant;
    }


    function getParticipantInformations(address _issuer) public view returns(address, uint) {
        return (meters[_issuer].add, meters[_issuer].balance);
    }


    // ########### Place offer functions ###################################################################################################
    function makeOffer(bool _bs, uint _price, uint _quantity) public {
        if(_bs){
            marketListB[indexTime].push(
                Offer({user:msg.sender, buyer_seller: _bs, price: _price, quantity: _quantity, idxTime: indexTime})
            );

            priceB[indexTime].push(_price);
            idxB[indexTime].push(priceB[indexTime].length - 1);
        }else{
            marketListS[indexTime].push(
                Offer({user:msg.sender, buyer_seller: _bs, price: _price, quantity: _quantity, idxTime: indexTime})
            );

            priceS[indexTime].push(_price);
            idxS[indexTime].push(priceS[indexTime].length - 1);
        }
    }


    function getOffersInfo(address _sender) public view returns(uint, uint){
        Offer memory _contract = adrsOffer[_sender];
        return(_contract.price, _contract.quantity);
    }


    function setIndexTime(uint _idxTime) public returns(bool){
        indexTime = _idxTime;
        return true;
    }


    // ########### Auction mechanism functions ############################################################################################
    function matching() public returns(uint q, uint p){
        // Verifica lo stato del mercato
        if((priceS[indexTime].length == 0) && (priceB[indexTime].length > 0)){
            // Tutti pagano al prezzo di acquisto dalla rete
            for(uint i = 0; i < marketListB[indexTime].length; i++){
                transfer(marketListB[indexTime][i].user, Master, buyGrid, marketListB[indexTime][i].quantity);
            }
        }else if((priceS[indexTime].length > 0) && (priceB[indexTime].length == 0)){
            // Tutti vendono al prezzo di vendita della rete
            for(uint j = 0; j < marketListS[indexTime].length; j++){
                transfer(Master, marketListS[indexTime][j].user, sellGrid, marketListS[indexTime][j].quantity);
            }
        }else if((priceS[indexTime].length > 0) && (priceB[indexTime].length > 0)){
            // Eseguiamo intersezione del mercato
            // Sorting e update orderBook
            uint[] memory indexB = sort(priceB[indexTime], idxB[indexTime], true);
            uint[] memory indexS = sort(priceS[indexTime], idxS[indexTime], false);

            for(uint i = 0; i < indexB.length; i++){
                orderBook_B[indexTime].push(marketListB[indexTime][indexB[i]]);
            }
            for(uint j = 0; j < indexS.length; j++){
                orderBook_S[indexTime].push(marketListS[indexTime][indexS[j]]);
            }

            (q, p) = intrsc();
            for(uint i = 0; i < orderBook_B[indexTime].length; i++){
                transfer(orderBook_B[indexTime][i].user, Master, p, orderBook_B[indexTime][i].quantity);
            }

            for(uint j = 0; j < orderBook_S[indexTime].length; j++){
                transfer(Master, orderBook_S[indexTime][j].user, p, orderBook_B[indexTime][j].quantity);
            }

        }

        // Alla fine del matching incremetiamo il valore dell'indice intervallo
        // indexTime += 1;
    }


    function sum(uint[] memory _arr) pure internal returns(uint){
        uint result = 0;
        for (uint i = 0; i < _arr.length; i++) {
            result += _arr[i];
        }
        return result;
    }


    function min(uint[] memory _list) pure internal returns(uint){
        uint minvalue = 2**8 - 1;
        for (uint i = 0; i < _list.length; i++) {
            if(_list[i] < minvalue){
                minvalue = _list[i];
            }
        }
        return minvalue;
    }


    function getMinValue(uint[] memory _tmpSupply, uint[] memory _tmpDemand) pure public returns(uint){
        uint sumSupply = sum(_tmpSupply);
        uint sumDemand = sum(_tmpDemand);

        uint[] memory marketList = new uint[](2);
        marketList[0] = sumSupply;
        marketList[1] = sumDemand;

        uint minV = min(marketList);
        return minV;
    }


    function intrsc() view public returns(uint, uint){
        uint idx_D = 0;
        uint idx_S = 0;
        uint market_q = 0;
        uint market_p = 0;

        (uint[] memory _tmpDemand, uint[] memory demandCost, uint[] memory _tmpSupply, uint[] memory supplyCost) = getValues();

        uint minV = getMinValue(_tmpSupply, _tmpDemand);
        // min(marketList);

        while (minV > 0){
            if(demandCost[idx_D] >= supplyCost[idx_S]){
                if(_tmpDemand[idx_D] > _tmpSupply[idx_S]){
                    uint diff = _tmpDemand[idx_D] - _tmpSupply[idx_S];
                    market_q += _tmpSupply[idx_S];

                    uint[] memory _tmpList = new uint[](2);
                    _tmpList[0] = supplyCost[idx_S];
                    _tmpList[1] = demandCost[idx_D];
                    market_p = min(_tmpList);

                    _tmpSupply[idx_S] = 0;
                    _tmpDemand[idx_D] = diff;
                    idx_S += 1;
                }else if(_tmpDemand[idx_D] < _tmpSupply[idx_S]){
                    uint diff = _tmpSupply[idx_S] - _tmpDemand[idx_D];
                    market_q += _tmpDemand[idx_D];

                    uint[] memory _tmpList = new uint[](2);
                    _tmpList[0] = supplyCost[idx_S];
                    _tmpList[1] = demandCost[idx_D];
                    market_p = min(_tmpList);

                    _tmpDemand[idx_D] = 0;
                    _tmpSupply[idx_S] = diff;
                    idx_D += 1;
                }else if(_tmpDemand[idx_D] == _tmpSupply[idx_S]){
                    uint[] memory _tmpList = new uint[](2);
                    _tmpList[0] = supplyCost[idx_S];
                    _tmpList[1] = demandCost[idx_D];
                    market_p = min(_tmpList);

                    _tmpDemand[idx_D] = 0;
                    _tmpSupply[idx_S] = 0;
                    idx_D += 1;
                    idx_S += 1;
                }
            }else{
                break;
            }
            uint _minV = getMinValue(_tmpSupply, _tmpDemand);
            minV = _minV;
        }

        return (market_q, market_p);
    }


    function getValues() view public returns(uint[] memory, uint[] memory, uint[] memory, uint[] memory){
        uint[] memory _demand = new uint[](orderBook_B[indexTime].length);
        uint[] memory _supply = new uint[](orderBook_S[indexTime].length);
        uint[] memory _demandC = new uint[](orderBook_B[indexTime].length);
        uint[] memory _supplyC = new uint[](orderBook_S[indexTime].length);

        for(uint i = 0; i < orderBook_B[indexTime].length; i++){
            _demand[i] = orderBook_B[indexTime][i].quantity;
            _demandC[i] = orderBook_B[indexTime][i].price;
        }

        for(uint j = 0; j < orderBook_S[indexTime].length; j++){
            _supply[j] = orderBook_S[indexTime][j].quantity;
            _supplyC[j] = orderBook_S[indexTime][j].price;
        }
        return (_demand, _demandC, _supply, _supplyC);
    }


    // ########### Sorting functions #######################################################################################################
    function sort(uint[] memory data, uint[] memory idx, bool method) internal returns(uint[] memory) {
        if(method){
            quickSort_down(data, idx, int(0), int(data.length - 1));
        }else{
            quickSort_up(data, idx, int(0), int(data.length - 1));
        }
       return idx;
    }


    // Sorting crescente
    function quickSort_up(uint[] memory arr, uint[] memory _idx, int left, int right) internal {
        int i = left;
        int j = right;
        if(i==j) return;
        uint pivot = arr[uint(left + (right - left) / 2)];
        while (i <= j) {
            while (arr[uint(i)] < pivot) i++;
            while (pivot < arr[uint(j)]) j--;
            if (i <= j) {
                (arr[uint(i)], arr[uint(j)]) = (arr[uint(j)], arr[uint(i)]);
                (_idx[uint(i)], _idx[uint(j)]) = (_idx[uint(j)], _idx[uint(i)]);
                i++;
                j--;
            }
        }
        if (left < j)
            quickSort_up(arr, _idx, left, j);
        if (i < right)
            quickSort_up(arr, _idx, i, right);
    }


    // Sorting decrescente
    function quickSort_down(uint[] memory arr, uint[] memory _idx, int left, int right) internal {
        int i = left;
        int j = right;
        if(i==j) return;
        uint pivot = arr[uint(left + (right - left) / 2)];
        while (i <= j) {
            while (arr[uint(i)] > pivot) i++;
            while (pivot > arr[uint(j)]) j--;
            if (i <= j) {
                (arr[uint(j)], arr[uint(i)]) = (arr[uint(i)], arr[uint(j)]);
                (_idx[uint(j)], _idx[uint(i)]) = (_idx[uint(i)], _idx[uint(j)]);
                i++;
                j--;
            }
        }
        if (left < j)
            quickSort_down(arr, _idx, left, j);
        if (i < right)
            quickSort_down(arr, _idx, i, right);
    }

}
