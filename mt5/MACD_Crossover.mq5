//+------------------------------------------------------------------+
//|                                               MACD_Crossover.mq5 |
//|                                  Copyright 2026, Antigravity AI  |
//|                                       https://github.com/google  |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, Antigravity AI"
#property link      "https://github.com/google"
#property version   "1.00"
#property description "Expert Advisor executing trades on custom MACD crossover signals."
#property description "Calculates MACD manually without using iMACD."
#property strict

//--- Inputs
input group "Indicator Settings"
input int FastEMA = 12;            // Fast EMA Period
input int SlowEMA = 26;            // Slow EMA Period
input int SignalEMA = 9;           // Signal Line EMA Period
input int HistoryDepth = 400;      // Number of bars for EMA convergence (min 200)

input group "Trading Settings"
input double LotSize = 0.10;       // Trade Lot Size
input int StopLoss = 0;            // Stop Loss in points (0 = disabled)
input int TakeProfit = 0;          // Take Profit in points (0 = disabled)
input ulong MagicNumber = 881226;  // EA Magic Number

//--- Global Variables
datetime lastBarTime = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
// Check input validity
   if(FastEMA <= 0 || SlowEMA <= 0 || SignalEMA <= 0 || HistoryDepth < 50)
     {
      Print("Error: Invalid indicator parameter settings in OnInit.");
      return INIT_PARAMETERS_INCORRECT;
     }

   if(LotSize <= 0)
     {
      Print("Error: Lot size must be greater than zero.");
      return INIT_PARAMETERS_INCORRECT;
     }

// Initialize the new bar checker to current bar's time
// This prevents executing signal checks on a partially formed candle on startup
   IsNewBar();

   PrintFormat("Custom MACD EA initialized. FastEMA=%d, SlowEMA=%d, SignalEMA=%d, Magic=%d",
               FastEMA, SlowEMA, SignalEMA, MagicNumber);

   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   Print("Custom MACD EA deinitialized. Reason code: ", reason);
  }

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
  {
// Check if a new candle/bar has opened
   if(!IsNewBar())
      return;

   double macdLine[];
   double signalLine[];

// Calculate MACD manually. We need values up to index 2 (completed candle 1 and previous candle 2)
   if(!CalculateManualMACD(macdLine, signalLine, HistoryDepth))
     {
      Print("Error: Manual MACD calculation failed. Skipping this tick.");
      return;
     }

// We execute signals ONLY on completed candles:
// Bar 1 = last completed candle
// Bar 2 = candle before that

// Buy Signal: MACD Line crosses ABOVE Signal Line
   bool buySignal = (macdLine[1] > signalLine[1]) && (macdLine[2] <= signalLine[2]);

// Sell Signal: MACD Line crosses BELOW Signal Line
   bool sellSignal = (macdLine[1] < signalLine[1]) && (macdLine[2] >= signalLine[2]);

// Run Trade Management
   if(buySignal)
     {
      PrintFormat("Signal: BUY Crossover. MACD[1]=%.6f, Signal[1]=%.6f | MACD[2]=%.6f, Signal[2]=%.6f",
                  macdLine[1], signalLine[1], macdLine[2], signalLine[2]);

      ulong activeTicket = 0;
      ENUM_POSITION_TYPE activeType = POSITION_TYPE_BUY;
      double activeVolume = 0.0;

      if(GetActivePosition(activeTicket, activeType, activeVolume))
        {
         if(activeType == POSITION_TYPE_SELL)
           {
            PrintFormat("Action: Closing Sell Position #%d to execute Buy Signal.", activeTicket);
            if(ClosePosition(activeTicket, activeVolume, activeType))
              {
               OpenPosition(ORDER_TYPE_BUY, LotSize);
              }
           }
         else
           {
            PrintFormat("Action: Buy Position already exists (#%d). Skipping duplicate entry.", activeTicket);
           }
        }
      else
        {
         OpenPosition(ORDER_TYPE_BUY, LotSize);
        }
     }
   else
      if(sellSignal)
        {
         PrintFormat("Signal: SELL Crossover. MACD[1]=%.6f, Signal[1]=%.6f | MACD[2]=%.6f, Signal[2]=%.6f",
                     macdLine[1], signalLine[1], macdLine[2], signalLine[2]);

         ulong activeTicket = 0;
         ENUM_POSITION_TYPE activeType = POSITION_TYPE_SELL;
         double activeVolume = 0.0;

         if(GetActivePosition(activeTicket, activeType, activeVolume))
           {
            if(activeType == POSITION_TYPE_BUY)
              {
               PrintFormat("Action: Closing Buy Position #%d to execute Sell Signal.", activeTicket);
               if(ClosePosition(activeTicket, activeVolume, activeType))
                 {
                  OpenPosition(ORDER_TYPE_SELL, LotSize);
                 }
              }
            else
              {
               PrintFormat("Action: Sell Position already exists (#%d). Skipping duplicate entry.", activeTicket);
              }
           }
         else
           {
            OpenPosition(ORDER_TYPE_SELL, LotSize);
           }
        }
  }

//+------------------------------------------------------------------+
//| Check if a new bar has opened                                    |
//+------------------------------------------------------------------+
bool IsNewBar()
  {
   datetime currentBarTime = (datetime)SeriesInfoInteger(_Symbol, PERIOD_CURRENT, SERIES_LASTBAR_DATE);

   if(currentBarTime == 0)
     {
      // Timeseries data not loaded/ready yet
      return false;
     }

   if(currentBarTime != lastBarTime)
     {
      if(lastBarTime == 0)
        {
         // First run of the EA: initialize bar time and wait for next candle close
         lastBarTime = currentBarTime;
         return false;
        }
      lastBarTime = currentBarTime;
      return true;
     }

   return false;
  }

//+------------------------------------------------------------------+
//| Custom MACD Calculation (No iMACD)                               |
//| Recreates EMA(12), EMA(26) and EMA(MACD, 9) using Close prices    |
//+------------------------------------------------------------------+
bool CalculateManualMACD(double &macd[], double &signal[], int historySize)
  {
   double closePrices[];
   ArraySetAsSeries(closePrices, true);

// Copy Close prices of the last 'historySize' bars
   int copied = CopyClose(_Symbol, PERIOD_CURRENT, 0, historySize, closePrices);
   if(copied < historySize)
     {
      PrintFormat("Error: CopyClose failed. Copied: %d, expected: %d", copied, historySize);
      return false;
     }

   double emaFast[];
   double emaSlow[];

// Resize calculation buffers
   if(ArrayResize(emaFast, historySize) < 0 ||
      ArrayResize(emaSlow, historySize) < 0 ||
      ArrayResize(macd, historySize) < 0 ||
      ArrayResize(signal, historySize) < 0)
     {
      Print("Error: Resizing custom indicator arrays failed.");
      return false;
     }

// Ensure buffers behave as series (index 0 is current bar, index size-1 is oldest)
   ArraySetAsSeries(emaFast, true);
   ArraySetAsSeries(emaSlow, true);
   ArraySetAsSeries(macd, true);
   ArraySetAsSeries(signal, true);

   double kFast = 2.0 / (FastEMA + 1.0);
   double kSlow = 2.0 / (SlowEMA + 1.0);
   double kSignal = 2.0 / (SignalEMA + 1.0);

// 1. Initialize EMA values at the oldest copied bar (index historySize - 1)
   emaFast[historySize - 1] = closePrices[historySize - 1];
   emaSlow[historySize - 1] = closePrices[historySize - 1];
   macd[historySize - 1] = emaFast[historySize - 1] - emaSlow[historySize - 1];

// 2. Loop forward in time (index counts down) to calculate Fast EMA, Slow EMA and MACD Line
   for(int i = historySize - 2; i >= 0; i--)
     {
      emaFast[i] = (closePrices[i] * kFast) + (emaFast[i + 1] * (1.0 - kFast));
      emaSlow[i] = (closePrices[i] * kSlow) + (emaSlow[i + 1] * (1.0 - kSlow));
      macd[i] = emaFast[i] - emaSlow[i];
     }

// 3. Initialize Signal Line at the oldest bar (index historySize - 1)
   signal[historySize - 1] = macd[historySize - 1];

// 4. Loop forward in time (index counts down) to calculate Signal Line
   for(int i = historySize - 2; i >= 0; i--)
     {
      signal[i] = (macd[i] * kSignal) + (signal[i + 1] * (1.0 - kSignal));
     }

   return true;
  }

//+------------------------------------------------------------------+
//| Find active symbol position matching Symbol and Magic Number     |
//+------------------------------------------------------------------+
bool GetActivePosition(ulong &ticket, ENUM_POSITION_TYPE &type, double &volume)
  {
   int total = PositionsTotal();
   for(int i = total - 1; i >= 0; i--)
     {
      ulong posTicket = PositionGetTicket(i);
      if(posTicket > 0)
        {
         if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
            PositionGetInteger(POSITION_MAGIC) == MagicNumber)
           {
            ticket = posTicket;
            type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
            volume = PositionGetDouble(POSITION_VOLUME);
            return true;
           }
        }
     }
   return false;
  }

//+------------------------------------------------------------------+
//| Close a position by ticket using MqlTradeRequest                 |
//+------------------------------------------------------------------+
bool ClosePosition(ulong ticket, double volume, ENUM_POSITION_TYPE type)
  {
   MqlTradeRequest request;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(result);

   request.action = TRADE_ACTION_DEAL;
   request.symbol = _Symbol;
   request.volume = volume;
   request.position = ticket;
   request.magic = MagicNumber;
   request.deviation = 10;

// For Buy position close: Sell. For Sell position close: Buy.
   if(type == POSITION_TYPE_BUY)
     {
      request.type = ORDER_TYPE_SELL;
      request.price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
     }
   else
      if(type == POSITION_TYPE_SELL)
        {
         request.type = ORDER_TYPE_BUY;
         request.price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
        }
      else
        {
         PrintFormat("Error: Invalid position type %d for ticket %d", type, ticket);
         return false;
        }

   if(!OrderSend(request, result))
     {
      PrintFormat("Error: OrderSend failed for ClosePosition #%d. Err: %d", ticket, GetLastError());
      return false;
     }

   if(result.retcode != TRADE_RETCODE_DONE && result.retcode != TRADE_RETCODE_PLACED)
     {
      PrintFormat("Error: Close trade rejected by broker. Ticket #%d, Retcode: %d", ticket, result.retcode);
      return false;
     }

   PrintFormat("Success: Closed position #%d", ticket);
   return true;
  }

//+------------------------------------------------------------------+
//| Open a new market position using MqlTradeRequest                 |
//+------------------------------------------------------------------+
bool OpenPosition(ENUM_ORDER_TYPE orderType, double volume)
  {
   MqlTradeRequest request;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(result);

   request.action = TRADE_ACTION_DEAL;
   request.symbol = _Symbol;
   request.volume = volume;
   request.type = orderType;
   request.magic = MagicNumber;
   request.deviation = 10;

   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

   if(orderType == ORDER_TYPE_BUY)
     {
      request.price = ask;
      if(StopLoss > 0)
         request.sl = ask - StopLoss * point;
      if(TakeProfit > 0)
         request.tp = ask + TakeProfit * point;
     }
   else
      if(orderType == ORDER_TYPE_SELL)
        {
         request.price = bid;
         if(StopLoss > 0)
            request.sl = bid + StopLoss * point;
         if(TakeProfit > 0)
            request.tp = bid - TakeProfit * point;
        }
      else
        {
         PrintFormat("Error: Invalid order type %d in OpenPosition", orderType);
         return false;
        }

   if(!OrderSend(request, result))
     {
      PrintFormat("Error: OrderSend failed for OpenPosition. Err: %d", GetLastError());
      return false;
     }

   if(result.retcode != TRADE_RETCODE_DONE && result.retcode != TRADE_RETCODE_PLACED)
     {
      PrintFormat("Error: Open trade request rejected by broker. Retcode: %d", result.retcode);
      return false;
     }

   PrintFormat("Success: Position opened. Ticket: #%d, Deal: #%d", result.order, result.deal);
   return true;
  }
//+------------------------------------------------------------------+
