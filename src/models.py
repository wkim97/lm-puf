import torch
import torch.nn as nn


class PUFModel(nn.Module):
    """7-layer MLP (`mlp_large`)."""
    def __init__(self, input_dim=5, output_dim=1024):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, 128)
        self.fc2 = nn.Linear(128, 256)
        self.fc3 = nn.Linear(256, 512)
        self.fc4 = nn.Linear(512, 1024)
        self.fc5 = nn.Linear(1024, 2048)
        self.fc6 = nn.Linear(2048, 2048)
        self.fc7 = nn.Linear(2048, output_dim)
        self.act = nn.ReLU()

    def forward(self, x):
        x = self.act(self.fc1(x))
        x = self.act(self.fc2(x))
        x = self.act(self.fc3(x))
        x = self.act(self.fc4(x))
        x = self.act(self.fc5(x))
        x = self.act(self.fc6(x))
        return self.fc7(x)


class RegressionModel(nn.Module):
    """logistic-regression baseline."""
    def __init__(self, input_dim=5, output_dim=1024):
        super().__init__()
        self.fc = nn.Linear(input_dim, output_dim)

    def forward(self, x):
        return self.fc(x)


class MLP(nn.Module):
    def __init__(self, input_dim, output_dim, hidden_dims):
        super().__init__()
        layers = []
        prev = input_dim
        for h in hidden_dims:
            layers.append(nn.Linear(prev, h))
            layers.append(nn.ReLU())
            prev = h
        layers.append(nn.Linear(prev, output_dim))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


class CNN1D(nn.Module):
    """
    Treats the 5 input features as a sequence of length 5 with 1 channel.
    Uses 1D convolutions with increasing channel depth, then flattens to predict bits.
    """
    def __init__(self, input_dim=5, output_dim=1024, base_channels=64):
        super().__init__()
        c = base_channels
        self.conv1 = nn.Conv1d(1, c, kernel_size=3, padding=1)
        self.conv2 = nn.Conv1d(c, c * 2, kernel_size=3, padding=1)
        self.conv3 = nn.Conv1d(c * 2, c * 4, kernel_size=3, padding=1)
        self.conv4 = nn.Conv1d(c * 4, c * 8, kernel_size=3, padding=1)
        self.act = nn.ReLU()
        flat_dim = c * 8 * input_dim
        self.fc1 = nn.Linear(flat_dim, 2048)
        self.fc2 = nn.Linear(2048, output_dim)

    def forward(self, x):
        # x: [B, input_dim] -> [B, 1, input_dim]
        x = x.unsqueeze(1)
        x = self.act(self.conv1(x))
        x = self.act(self.conv2(x))
        x = self.act(self.conv3(x))
        x = self.act(self.conv4(x))
        x = x.flatten(1)
        x = self.act(self.fc1(x))
        return self.fc2(x)


class TransformerModel(nn.Module):
    """
    Embeds each of the 5 scalar inputs as a token, runs a small transformer encoder,
    then pools and projects to output bits.
    """
    def __init__(self, input_dim=5, output_dim=1024, d_model=128, nhead=4, num_layers=4, dim_feedforward=512):
        super().__init__()
        self.input_dim = input_dim
        self.token_embed = nn.Linear(1, d_model)
        self.pos_embed = nn.Parameter(torch.randn(1, input_dim, d_model) * 0.02)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            batch_first=True,
            activation='gelu',
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.head = nn.Sequential(
            nn.Linear(d_model * input_dim, 2048),
            nn.GELU(),
            nn.Linear(2048, output_dim),
        )

    def forward(self, x):
        # x: [B, input_dim] -> [B, input_dim, 1] -> [B, input_dim, d_model]
        tokens = self.token_embed(x.unsqueeze(-1)) + self.pos_embed
        h = self.encoder(tokens)  # [B, input_dim, d_model]
        h = h.flatten(1)
        return self.head(h)


def get_model(model_type: str, input_dim: int = 5, output_dim: int = 1024) -> nn.Module:
    """
    Factory for PUF prediction models.

    Available types:
      - regression     : logistic-regression
      - mlp_medium     : 5-layer MLP
      - mlp_large      : 7-layer MLP
      - mlp_xlarge     : 9-layer wider MLP
      - cnn1d          : 1D CNN over the 5 features
      - transformer    : small transformer encoder over 5 tokens
    """
    mt = model_type.lower()
    if mt == "regression":
        return RegressionModel(input_dim, output_dim)
    if mt == "mlp_medium":
        return MLP(input_dim, output_dim, hidden_dims=[128, 512, 1024, 2048, 2048])
    if mt == "mlp_large":
        return PUFModel(input_dim, output_dim)
    if mt == "mlp_xlarge":
        return MLP(input_dim, output_dim, hidden_dims=[256, 1024, 2048, 4096, 4096, 4096, 2048, 2048])
    if mt == "cnn1d":
        return CNN1D(input_dim, output_dim, base_channels=64)
    if mt == "transformer":
        return TransformerModel(input_dim, output_dim, d_model=128, nhead=4, num_layers=4, dim_feedforward=512)
    raise ValueError(f"Unknown model_type: {model_type}")
