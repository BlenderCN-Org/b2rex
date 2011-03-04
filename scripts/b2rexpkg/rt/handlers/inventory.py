from .base import Handler
from pyogp.lib.client.inventory import UDP_Inventory
from pyogp.lib.client.inventory import InventoryItem
import uuid
import random
from pyogp.lib.base.datatypes import UUID
from pyogp.lib.base.message.message import Message, Block

def sendRezObject(agent, inventory_item, RayStart, RayEnd, FromTaskID = UUID(), BypassRaycast = 1,  RayTargetID = UUID(), RayEndIsIntersection = False, RezSelected = False, RemoveItem = True, ItemFlags = 0, GroupMask = 0, EveryoneMask = 0, NextOwnerMask = 0):
    """ sends a RezObject packet to a region """

    packet = Message('RezObject',
                    Block('AgentData',
                          AgentID = agent.agent_id,
                          SessionID = agent.session_id,
                          GroupID = agent.ActiveGroupID),
                    Block('RezData',
                          FromTaskID = UUID(str(FromTaskID)),
                          BypassRaycast = BypassRaycast,
                          RayStart = RayStart,
                          RayEnd = RayEnd,
                          RayTargetID = UUID(str(RayTargetID)),
                          RayEndIsIntersection = RayEndIsIntersection,
                          RezSelected = RezSelected,
                          RemoveItem = RemoveItem,
                          ItemFlags = ItemFlags,
                          GroupMask = GroupMask,
                          EveryoneMask = EveryoneMask,
                          NextOwnerMask = NextOwnerMask),
                    Block('InventoryData',
                          ItemID = inventory_item.ItemID,
                          FolderID = inventory_item.FolderID,
                          CreatorID = inventory_item.CreatorID,
                          OwnerID = inventory_item.OwnerID,
                          GroupID = inventory_item.GroupID,
                          BaseMask = inventory_item.BaseMask,
                          OwnerMask = inventory_item.OwnerMask,
                          GroupMask = inventory_item.GroupMask,
                          EveryoneMask = inventory_item.EveryoneMask,
                          GroupOwned = inventory_item.GroupOwned,
                          TransactionID = UUID(),
                          Type = inventory_item.Type,
                          InvType = inventory_item.InvType,
                          Flags = inventory_item.Flags,
                          SaleType = inventory_item.SaleType,
                          SalePrice = inventory_item.SalePrice,
                          Name = inventory_item.Name,
                          Description = inventory_item.Description,
                          CreationDate = inventory_item.CreationDate,
                          CRC = inventory_item.CRC,
                          NextOwnerMask = inventory_item.NextOwnerMask))

    agent.region.enqueue_message(packet)
class InventoryHandler(Handler):
    def onAgentConnected(self, agent):
        self.inventory = UDP_Inventory(agent)

    def onRegionConnect(self, region):
        res = region.message_handler.register("InventoryDescendents")
        res.subscribe(self.onInventoryDescendents)
        res = region.message_handler.register("UpdateCreateInventoryItem")
        res.subscribe(self.onUpdateCreateInventoryItem)
        self.inventory.enable_callbacks()

    def onRegionConnected(self, region):
        client = self.manager.client

        # send inventory skeleton
        if hasattr(client, 'login_response') and 'inventory-skeleton' in client.login_response:
            self.out_queue.put(["InventorySkeleton",  client.login_response['inventory-skeleton']])

        self.inventory._parse_folders_from_login_response()

    def processFetchInventoryDescendents(self, *args):
        self.logger.debug('inventory processFetchInventoryDescendents')
        self.inventory.sendFetchInventoryDescendentsRequest(*args)

    def processRezObject(self, item_id, raystart, rayend):
        self.logger.debug('inventory processRezObject')
        items = [_item for _item in self.inventory.items if str(_item.ItemID) == item_id]

        if len(items):
            item = items[0]
        else:
            return

        self.logger.debug('sendRezObject')
        
        sendRezObject(self.manager.client, item, raystart, rayend)

    def serializableInventory(self):
        folders = [{'Name' : member.Name, 'ParentID' : str(member.ParentID), 'FolderID' : str(member.FolderID), 'Descendents' : int(member.Descendents)} for member in self.inventory.folders]
        items = [{'Name' : member.Name, 'FolderID' : str(member.FolderID), 'AssetID' : str(member.AssetID), 'ItemID' : str(member.ItemID), 'InvType' : member.InvType} for member in self.inventory.items] 
        return folders, items

    def onInventoryDescendents(self, packet):
        logger = self.logger
        logger.debug('onInventoryDescendents')
        folder_id = packet['AgentData'][0]['FolderID']
        folders, items = self.serializableInventory()
        

        self.out_queue.put(['InventoryDescendents', str(folder_id), folders, items])


    def onUpdateCreateInventoryItem(self, packet):
        logger = self.logger
        logger.debug('onUpdateCreateInventoryItem')

        inv_data = packet['InventoryData'][0] 
        item = InventoryItem(inv_data['ItemID'],
                             inv_data['FolderID'],
                             inv_data['CreatorID'],
                             inv_data['OwnerID'],
                             inv_data['GroupID'],
                             inv_data['BaseMask'],
                             inv_data['OwnerMask'],
                             inv_data['GroupMask'],
                             inv_data['EveryoneMask'],
                             inv_data['NextOwnerMask'],
                             inv_data['GroupOwned'],
                             inv_data['AssetID'],
                             inv_data['Type'],
                             inv_data['InvType'],
                             inv_data['Flags'],
                             inv_data['SaleType'],
                             inv_data['SalePrice'],
                             inv_data['Name'],
                             inv_data['Description'],
                             inv_data['CreationDate'],
                             inv_data['CRC'])

        self.addInventoryItem(item)


    def addInventoryItem(self, item):
        self.inventory._store_inventory_item(item)

        for folder in self.inventory.folders: 
            if str(folder.FolderID) == str(item.FolderID):
                folder.Descendents += 1
                break

        folders, items = self.serializableInventory()
 
        self.out_queue.put(['InventoryDescendents', str(item.FolderID), folders, items])


    def removeInventoryItem(self, item_id):
        items = self.inventory.items
        folders = self.inventory.folders

        folder_id = None
        for _item in items: 
            if str(_item.ItemID) == str(item_id):
                folder_id = str(_item.FolderID)
                items.remove(_item)
                break

        if folder_id:
            for folder in folders: 
                if str(folder.FolderID) == str(folder_id):
                    folder.Descendents -= 1
                    break

    def findItem(self, item_id):
        items = self.inventory.items

        for _item in items: 
            if str(_item.ItemID) == str(item_id):
                return _item

    def processUpdateInventoryItem(self, item_id, trID, asset_type, inv_type, name, desc):
        agent = self.manager.client
        item = self.findItem(item_id)
        print("UPDATING INVENTORY ITEM", item, item_id)
        if item:
            self.sendUpdateInventoryItem(agent, trID, [item])

    def sendUpdateInventoryItem(self, agent, transaction_id, inventory_items = []):
        """ sends an UpdateInventoryItem packet to a region 

        this function expects an InventoryItem instance already with updated data
        """
        packet = Message('UpdateInventoryItem',
                        Block('AgentData',
                                AgentID = agent.agent_id,
                                SessionID = agent.session_id,
                                TransactionID = UUID()),
                        *[Block('InventoryData',
                                ItemID = item.ItemID,
                                FolderID = item.FolderID,
                                CallbackID = random.randint (0, pow (2, 32)-1),
                                CreatorID = item.CreatorID,
                                OwnerID = item.OwnerID,
                                GroupID = item.GroupID,
                                BaseMask = item.BaseMask,
                                OwnerMask = item.OwnerMask,
                                GroupMask = item.GroupMask,
                                EveryoneMask = item.EveryoneMask,
                                NextOwnerMask = item.NextOwnerMask,
                                GroupOwned = item.GroupOwned,
                                TransactionID = UUID(transaction_id),
                                Type = item.Type,
                                InvType = item.InvType,
                                Flags = item.Flags,
                                SaleType = item.SaleType,
                                SalePrice = item.SalePrice,
                                Name = item.Name,
                                Description = item.Description,
                                CreationDate = item.CreationDate,
                                CRC = item.CRC) for item in inventory_items])

        agent.region.enqueue_message(packet)


    def processCreateInventoryItem(self, trID, asset_type, inv_type, name, desc):
        wearable_type = 0
        agent = self.manager.client
        next_owner_permission = 0
        print("processCreateInventoryItem", trID, asset_type)
        self.inventory.send_CreateInventoryItem(agent.agent_id,
                                      agent.session_id,
                                      0,
                                      UUID(),
                                      UUID(trID),
                                      next_owner_permission,
                                      asset_type,
                                      inv_type,
                                      wearable_type,
                                      name,
                                      desc)



    def processRemoveInventoryItem(self, item_id):
        logger = self.logger
        logger.debug('processRemoveIntenvoryItem')
        
        self.removeInventoryItem(item_id)

        client = self.manager.client
        self.inventory.send_RemoveInventoryItem(client.agent_id, client.session_id, UUID(str(item_id)))

