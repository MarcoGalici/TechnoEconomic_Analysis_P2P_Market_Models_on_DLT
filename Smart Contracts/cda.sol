// "SPDX-License-Identifier: UNLICENSED"

pragma solidity >=0.4.23;

import "./safemath.sol";

contract test{

    using safemath for uint256;

    address public Master;
    // intervalli temporali
    uint public indexTime;

    uint public sellGrid;
    uint public buyGrid;

    constructor(address M) {
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

    mapping(address => Offer) public offers_adr;

    mapping(uint => Offer[]) public marketList;
    mapping(uint => Offer[]) public orderBook;

    mapping(uint => Contract[]) public transactions;

    mapping(uint => uint[]) public priceSeller;
    mapping(uint => uint[]) public idxSeller;
    mapping(uint => address[]) public adrSeller;

    mapping(uint => uint[]) public priceBuyer;
    mapping(uint => uint[]) public idxBuyer;
    mapping(uint => address[]) public adrBuyer;


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

        transactions[indexTime].push(Contract({seller: receiver, buyer: sender, price: numTokens, quantity: amount}));

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

        // _bs -->  true = buyer

        // _bs -->  false = seller

        Offer memory _bid = Offer({user:msg.sender, buyer_seller: _bs, price: _price, quantity: _quantity, idxTime: indexTime});

        offers_adr[msg.sender] = _bid;

        marketList[indexTime].push(_bid);

        // Add price, address and index in mapping (useful for matching function)
        if(_bs){
            // Buyer
            priceBuyer[indexTime].push(_price);
            idxBuyer[indexTime].push(priceBuyer[indexTime].length - 1);
            adrBuyer[indexTime].push(msg.sender);
        }else{
            // Seller
            priceSeller[indexTime].push(_price);
            idxSeller[indexTime].push(priceSeller[indexTime].length - 1);
            adrSeller[indexTime].push(msg.sender);
        }
    }


    function getOffersInfo(address _sender) public view returns(uint, uint){
        Offer memory _contract = offers_adr[_sender];
        return(_contract.price, _contract.quantity);
    }


    function setIndexTime(uint _idxTime) public returns(bool){
        indexTime = _idxTime;
        return true;
    }


    // ########### Auction mechanism functions ############################################################################################
    function _performMatching() public returns(uint){
        uint i = 0;
        (bool bb, bool sb) = getLengthBS();
        uint maxIt = (marketList[indexTime].length - 1);
        if(bb == true && sb == true){
            // Offerte Buy & Sell
            // uint maxIt = (marketList[indexTime].length - 1);
            _sortBook();

            while(i <= maxIt){
                i = _matchnowhile(i);
            }
        }else if(bb == false && sb == true){
            // Offerte only Sell
            // uint maxIt = (marketList[indexTime].length - 1);

            while(i <= maxIt){
                i = _matchonlybs(i, false);
            }
        }else if(bb == true && sb == false){
            // Offerte only Buy
            // uint maxIt = (marketList[indexTime].length - 1);

            while(i <= maxIt){
                i = _matchonlybs(i, true);
            }
        }
        return i;
    }


    function _sortBook() public {
        // NOTA: se non dovessero esserci buyer o seller è un problema (restituisce errore perché legge qualcosa che non esiste)
        (uint[] memory priceS, uint[] memory indexS) = sort(priceSeller[indexTime], idxSeller[indexTime], false);
        (uint[] memory priceB, uint[] memory indexB) = sort(priceBuyer[indexTime], idxBuyer[indexTime], true);
        uint itB = priceB.length;

        uint itS = priceS.length;

        uint i = 0;
        while(i < (itB+itS)){
            if(i < itB){
                address _buyer = adrBuyer[indexTime][indexB[i]];
                orderBook[indexTime].push(offers_adr[_buyer]);
            }else{
                address _seller = adrSeller[indexTime][indexS[i-itB]];
                orderBook[indexTime].push(offers_adr[_seller]);
            }
            i += 1;
        }
    }


    function _matchnowhile(uint _idx) public returns(uint){
        uint itB = priceBuyer[indexTime].length;
        // uint itS = priceSeller[indexTime].length;

        if(_idx < itB){
            (Offer memory osBid, bool check, uint idxSlr) = getosB();
            uint prcSeller = osBid.price;
            uint amntSeller = osBid.quantity;
            address adrsSeller = osBid.user;

            uint prcBuyer = orderBook[indexTime][_idx].price;
            address adrsBuyer = orderBook[indexTime][_idx].user;
            uint amntBuyer = orderBook[indexTime][_idx].quantity;


            if(check == true){
                if(prcSeller <= prcBuyer){
                    // uint indexS = getIndex(adrsSeller, prcSeller, amntSeller);
                    if(amntSeller > amntBuyer){
                        transfer(adrsBuyer, adrsSeller, safemath.div(prcSeller + prcBuyer, 2), amntBuyer);
                        // Riduciamo la quantità di energia in vendita del seller
                        orderBook[indexTime][idxSlr].quantity -= amntBuyer;

                        _idx += 1;
                    }else{
                        transfer(adrsBuyer, adrsSeller, safemath.div(prcSeller + prcBuyer, 2), amntSeller);
                        // Riduciamo la quantità di energia da acquistare del buyer
                        orderBook[indexTime][_idx].quantity -= amntSeller;

                        // Mettiamo a zero la quantità di energia in vendita del seller, perché venduta tutta
                        orderBook[indexTime][idxSlr].quantity = 0;
                    }
                }else{
                    // from Grid - Buyer
                    transfer(adrsBuyer, Master, buyGrid, amntBuyer);
                    _idx += 1;
                }
            }else{
                // from Grid - Buyer
                transfer(adrsBuyer, Master, buyGrid, amntBuyer);
                _idx += 1;
            }
        }else{
            // from Grid - Seller
            // Vuol dire che siamo arrivati ai sellers
            address adrsSrl = orderBook[indexTime][_idx].user;
            uint amntSrl = orderBook[indexTime][_idx].quantity;
            // Verifica che il seller abbia ancora energia da vendere
            if(amntSrl > 0){
                transfer(Master, adrsSrl, sellGrid, amntSrl);
            }
            _idx += 1;
        }
        return _idx;
    }


    function getosB() public view returns(Offer memory, bool, uint){
        uint lenB = priceBuyer[indexTime].length;
        uint lenS = priceSeller[indexTime].length;
        bool checkosB = false;
        uint _idx = 0;
        uint val = 0;
        Offer memory osBid = Offer({user:address(0), buyer_seller:false, price:0, quantity:0, idxTime:0});

        while(_idx < lenS){
            if(orderBook[indexTime][_idx + lenB].quantity == 0){
                _idx += 1;
            }else{
                checkosB = true;
                osBid = orderBook[indexTime][_idx + lenB];
                val = _idx + lenB;
                return(osBid, checkosB, val);
            }
        }
        return(osBid, checkosB, val);
    }


    function getLengthBS() public view returns(bool, bool){
        uint lB = priceBuyer[indexTime].length;
        uint lS = priceSeller[indexTime].length;
        bool _bb;
        bool _sb;
        // Check length of buyer offers
        if(lB > 0){
            _bb = true;
        }else{
            _bb = false;
        }
        // Check length of seller offers
        if(lS > 0){
            _sb = true;
        }else{
            _sb = false;
        }
        return (_bb, _sb);
    }


    function _matchonlybs(uint _idx, bool _buysell) public returns(uint){
        if(_buysell == true){
            address adrsByr = marketList[indexTime][_idx].user;
            uint amntByr = marketList[indexTime][_idx].quantity;

            transfer(adrsByr, Master, buyGrid, amntByr);
        }else{
            address adrsSrl = marketList[indexTime][_idx].user;
            uint amntSrl = marketList[indexTime][_idx].quantity;

            transfer(Master, adrsSrl, sellGrid, amntSrl);
        }
        _idx += 1;
        return _idx;
    }


    // ########### Sorting functions #######################################################################################################
    function sort(uint[] memory data, uint[] memory idx, bool method) public returns(uint[] memory, uint[] memory) {
        if(method){
            quickSort_down(data, idx, int(0), int(data.length - 1));
        }else{
            quickSort_up(data, idx, int(0), int(data.length - 1));
        }
       return (data, idx);
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
