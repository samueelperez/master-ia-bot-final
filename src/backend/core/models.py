from sqlalchemy import Column, Integer, String, JSON, TIMESTAMP, Float, ForeignKey, Text
from sqlalchemy.sql import func
from .db import Base

class Strategy(Base):
    __tablename__ = "strategies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    module_path = Column(String, nullable=True)
    params = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class Signal(Base):
    __tablename__ = "signals"
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    symbol = Column(String, index=True)
    timeframe = Column(String)
    params = Column(JSON)
    ts_enter = Column(TIMESTAMP(timezone=True))
    price_enter = Column(Float)
    sl = Column(Float)
    tp = Column(Float)
    ts_exit = Column(TIMESTAMP(timezone=True), nullable=True)
    price_exit = Column(Float, nullable=True)
    profit_loss = Column(Float, nullable=True)
    outcome = Column(String, nullable=True)

class StrategyPerformance(Base):
    __tablename__ = "strategy_performance"
    strategy_id = Column(Integer, ForeignKey("strategies.id"), primary_key=True)
    since = Column(TIMESTAMP(timezone=True), primary_key=True)
    until = Column(TIMESTAMP(timezone=True))
    total_trades = Column(Integer)
    wins = Column(Integer)
    losses = Column(Integer)
    win_rate = Column(Float)
    avg_return = Column(Float)
    max_drawdown = Column(Float)
    sharpe_ratio = Column(Float)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
