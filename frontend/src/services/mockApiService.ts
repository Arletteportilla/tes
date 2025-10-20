import { MockDataService } from './mockDataService';
import { 
  PollinationRecord, 
  GerminationRecord, 
  Plant, 
  PollinationType,
  SeedSource,
  GerminationCondition,
  PaginatedResponse,
  User
}la
y();
    let records = MockDataService.getGerminationRecords();

    // Apply search filter
    if (params.search) {
      const searchTerm = params.search.toLowerCase();
      records = records.filter(record => 
        record.plant.genus.toLowerCase().includes(searchTerm) ||
        record.plant.species.toLowerCase().includes(searchTerm) ||
        record.observations?.toLowerCase().includes(searchTerm)
      );
    }

    // Apply date filters
    if (params.date_from) {
      records = records.filter(record => record.germinationDate >= params.date_from);
    }
    if (params.date_to) {
      records = records.filter(record => record.germinationDate <= params.date_to);
    }

    // Apply plant filter
    if (params.plant) {
      records = records.filter(record => record.plant.id === params.plant);
    }

    return this.createPaginatedResponse(records, params.page, params.page_size);
  }

  static async getGerminationRecord(id: string): Promise<GerminationRecord> {
    await this.delay();
    const record = MockDataService.getGerminationRecords().find(r => r.id === id);
    if (!record) {
      throw new Error('Registro de germinación no encontrado');
    }
    return record;
  }

  static async createGerminationRecord(data: any, user: User): Promise<GerminationRecord> {
    await this.delay();
    
    // Validate required fields
    if (!data.plant) {
      throw new Error('Planta es requerida');
    }
    if (!data.seedSource) {
      throw new Error('Fuente de semillas es requerida');
    }
    if (!data.germinationDate) {
      throw new Error('Fecha de germinación es requerida');
    }
    if (!data.seedsPlanted || data.seedsPlanted < 1) {
      throw new Error('Cantidad de semillas debe ser mayor a 0');
    }
    if (!data.transplantDays || data.transplantDays < 1) {
      throw new Error('Días para trasplante debe ser mayor a 0');
    }

    return MockDataService.createGerminationRecord(data, user);
  }

  static async updateGerminationRecord(id: string, data: any): Promise<GerminationRecord> {
    await this.delay();
    const records = MockDataService.getGerminationRecords();
    const recordIndex = records.findIndex(r => r.id === id);
    
    if (recordIndex === -1) {
      throw new Error('Registro de germinación no encontrado');
    }

    // Update the record (simplified for mock)
    const updatedRecord = { ...records[recordIndex], ...data };
    
    // Recalculate germination rate if seedlings germinated is updated
    if (data.seedlingsGerminated !== undefined) {
      updatedRecord.germinationRate = Math.round((data.seedlingsGerminated / updatedRecord.seedsPlanted) * 100);
    }
    
    records[recordIndex] = updatedRecord;
    
    return updatedRecord;
  }

  static async deleteGerminationRecord(id: string): Promise<void> {
    await this.delay();
    const records = MockDataService.getGerminationRecords();
    const recordIndex = records.findIndex(r => r.id === id);
    
    if (recordIndex === -1) {
      throw new Error('Registro de germinación no encontrado');
    }

    records.splice(recordIndex, 1);
  }

  // Statistics API
  static async getPollinationStatistics(params: any = {}): Promise<any> {
    await this.delay();
    const records = MockDataService.getPollinationRecords();
    
    return {
      totalRecords: records.length,
      successfulRecords: records.filter(r => r.isSuccessful === true).length,
      pendingRecords: records.filter(r => r.isSuccessful === undefined).length,
      maturedRecords: records.filter(r => r.maturationConfirmed === true).length,
      byType: MockDataService.getPollinationTypes().map(type => ({
        type: type.name,
        count: records.filter(r => r.pollinationType.id === type.id).length
      })),
      byMonth: this.getRecordsByMonth(records, 'pollinationDate')
    };
  }

  static async getGerminationStatistics(params: any = {}): Promise<any> {
    await this.delay();
    const records = MockDataService.getGerminationRecords();
    
    const totalSeeds = records.reduce((sum, r) => sum + r.seedsPlanted, 0);
    const totalGerminated = records.reduce((sum, r) => sum + r.seedlingsGerminated, 0);
    
    return {
      totalRecords: records.length,
      totalSeeds,
      totalGerminated,
      averageGerminationRate: totalSeeds > 0 ? Math.round((totalGerminated / totalSeeds) * 100) : 0,
      successfulRecords: records.filter(r => r.isSuccessful === true).length,
      transplantedRecords: records.filter(r => r.transplantConfirmed === true).length,
      byCondition: MockDataService.getGerminationConditions().map(condition => ({
        condition: condition.climate,
        count: records.filter(r => r.germinationCondition.climate === condition.climate).length
      })),
      byMonth: this.getRecordsByMonth(records, 'germinationDate')
    };
  }

  private static getRecordsByMonth(records: any[], dateField: string): any[] {
    const monthCounts: { [key: string]: number } = {};
    
    records.forEach(record => {
      const date = new Date(record[dateField]);
      const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      monthCounts[monthKey] = (monthCounts[monthKey] || 0) + 1;
    });

    return Object.entries(monthCounts).map(([month, count]) => ({
      month,
      count
    })).sort((a, b) => a.month.localeCompare(b.month));
  }

  // Dashboard API
  static async getDashboardData(): Promise<any> {
    await this.delay();
    
    const pollinationRecords = MockDataService.getPollinationRecords();
    const germinationRecords = MockDataService.getGerminationRecords();
    
    // Recent activity (last 30 days)
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    
    const recentPollinations = pollinationRecords.filter(r => 
      new Date(r.pollinationDate) >= thirtyDaysAgo
    );
    
    const recentGerminations = germinationRecords.filter(r => 
      new Date(r.germinationDate) >= thirtyDaysAgo
    );

    return {
      summary: {
        totalPollinations: pollinationRecords.length,
        totalGerminations: germinationRecords.length,
        recentPollinations: recentPollinations.length,
        recentGerminations: recentGerminations.length,
        successRate: {
          pollination: pollinationRecords.length > 0 
            ? Math.round((pollinationRecords.filter(r => r.isSuccessful === true).length / pollinationRecords.length) * 100)
            : 0,
          germination: germinationRecords.length > 0
            ? Math.round(germinationRecords.reduce((sum, r) => sum + r.germinationRate, 0) / germinationRecords.length)
            : 0
        }
      },
      recentActivity: [
        ...recentPollinations.map(r => ({
          id: r.id,
          type: 'pollination',
          title: `Polinización ${r.pollinationType.name}`,
          description: `${r.motherPlant.genus} ${r.motherPlant.species}`,
          date: r.pollinationDate,
          status: r.isSuccessful === true ? 'success' : r.isSuccessful === false ? 'failed' : 'pending'
        })),
        ...recentGerminations.map(r => ({
          id: r.id,
          type: 'germination',
          title: 'Germinación',
          description: `${r.plant.genus} ${r.plant.species}`,
          date: r.germinationDate,
          status: r.isSuccessful === true ? 'success' : r.isSuccessful === false ? 'failed' : 'pending'
        }))
      ].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()).slice(0, 10),
      upcomingTasks: [
        ...pollinationRecords
          .filter(r => !r.maturationConfirmed && r.estimatedMaturationDate)
          .map(r => ({
            id: r.id,
            type: 'maturation_check',
            title: 'Verificar maduración',
            description: `${r.motherPlant.genus} ${r.motherPlant.species}`,
            dueDate: r.estimatedMaturationDate,
            priority: new Date(r.estimatedMaturationDate!) <= new Date() ? 'high' : 'medium'
          })),
        ...germinationRecords
          .filter(r => !r.transplantConfirmed && r.estimatedTransplantDate)
          .map(r => ({
            id: r.id,
            type: 'transplant_check',
            title: 'Verificar trasplante',
            description: `${r.plant.genus} ${r.plant.species}`,
            dueDate: r.estimatedTransplantDate,
            priority: new Date(r.estimatedTransplantDate!) <= new Date() ? 'high' : 'medium'
          }))
      ].sort((a, b) => new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime()).slice(0, 5)
    };
  }