{ pkgs, lib }:
let
  inventory = builtins.fromJSON (builtins.readFile ./inventory.json);
  system = pkgs.stdenv.hostPlatform.system;
  applies =
    item:
    builtins.elem system (
      item.systems or [
        "aarch64-darwin"
        "x86_64-darwin"
      ]
    );
  items = builtins.filter applies inventory.items;
  byProvider = provider: builtins.filter (item: item.provider == provider) items;
  resolve =
    item:
    lib.attrByPath (lib.splitString "." item.package)
      (throw "No nixpkgs attribute for ${item.name}: ${item.package}")
      pkgs;
  nixItems = byProvider "nix";
  package =
    item:
    if item.package == "python312" then
      pkgs.python312.withPackages (ps: [
        ps.pip
        ps.packaging
        ps.tkinter
      ])
    else if item.package == "corepack" then
      lib.lowPrio (resolve item)
    else
      resolve item;
in
{
  packages = map package (builtins.filter (item: item.category != "Fonts") nixItems);
  fonts = map resolve (builtins.filter (item: item.category == "Fonts") nixItems);
  casks = map (item: item.package) (byProvider "cask");
  brews = map (item: item.package) (byProvider "brew");
  masApps = builtins.listToAttrs (
    map (item: {
      inherit (item) name;
      value = item.package;
    }) (byProvider "mas")
  );
  assertions = map (
    item:
    let
      p = resolve item;
    in
    {
      assertion = lib.meta.availableOn pkgs.stdenv.hostPlatform p && !(p.meta.broken or false);
      message = "${item.name} (${item.package}) is unsupported or broken on ${system}; choose an explicit fallback in inventory.json.";
    }
  ) nixItems;
  audit = map (
    item:
    let
      p = resolve item;
    in
    {
      inherit (item) name package;
      version = p.version or "not reported";
      available = lib.meta.availableOn pkgs.stdenv.hostPlatform p;
      broken = p.meta.broken or false;
    }
  ) nixItems;
}
