# smart-postal-back-end/backend/models/gnn_predictor.py
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATConv

# This MUST match the class definition from your Colab training exactly
class ST_GNN_Predictor(nn.Module):
    def __init__(self, num_nodes, in_channels, hidden_dim=64, out_channels=3):
        super(ST_GNN_Predictor, self).__init__()
        self.gat1 = GATConv(in_channels, hidden_dim, heads=2, dropout=0.2)
        self.gat2 = GATConv(hidden_dim * 2, hidden_dim, heads=1, dropout=0.2)
        self.lstm = nn.LSTM(input_size=hidden_dim, hidden_size=hidden_dim, batch_first=True)
        
        # Decoder Heads
        self.fc_s = nn.Linear(hidden_dim, 1) # Small
        self.fc_m = nn.Linear(hidden_dim, 1) # Medium
        self.fc_l = nn.Linear(hidden_dim, 1) # Large
        self.fc_sigma = nn.Linear(hidden_dim, 1) # Uncertainty

    def forward(self, x, edge_index, edge_attr, hidden_state=None):
        num_nodes = x.size(1)
        x_graph = x.view(-1, x.size(-1)) 
        
        # Spatial (GAT)
        x_gat = self.gat1(x_graph, edge_index, edge_attr=edge_attr)
        x_gat = F.elu(x_gat)
        x_gat = self.gat2(x_gat, edge_index, edge_attr=edge_attr)
        x_gat = F.relu(x_gat)
        
        # Temporal (LSTM)
        x_seq = x_gat.view(1, num_nodes, -1)
        out_lstm, (hn, cn) = self.lstm(x_seq, hidden_state)
        out_final = out_lstm.squeeze(0)
        
        # Output
        pred_s = self.fc_s(out_final)
        pred_m = self.fc_m(out_final)
        pred_l = self.fc_l(out_final)
        sigma = torch.exp(self.fc_sigma(out_final))
        
        return pred_s, pred_m, pred_l, sigma, (hn, cn)